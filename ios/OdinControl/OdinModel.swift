import Foundation
import Observation

enum Agent: String, CaseIterable, Identifiable {
    case odin = "Odin", chatGPT = "ChatGPT"
    var id: Self { self }
}

enum Mode: String, CaseIterable, Identifiable {
    case start = "Start", plan = "Plan", work = "Work"
    var id: Self { self }

    func prompt(_ text: String, deeper: Bool, agent: Agent) -> String {
        if agent == .odin && text.hasPrefix("/") { return text }
        let guidance: String
        switch self {
        case .start: guidance = ""
        case .plan: guidance = "Help me plan this. Explain the steps, dependencies, and what to verify. Do not perform any actions."
        case .work: guidance = "Help me work through this. Give actionable steps and clear checks. Do not claim an action succeeded without a receipt."
        }
        let depth = deeper ? "Consider the alternatives, trade-offs, and uncertainties before answering." : ""
        return [guidance, depth, text].filter { !$0.isEmpty }.joined(separator: "\n\n")
    }
}

struct Pin: Codable, Identifiable {
    let id: UUID
    let messageID: String
    let agent: String
    let text: String
}

@MainActor @Observable
final class OdinModel {
    var agent: Agent = .odin
    var mode: Mode = .start
    var thinkLonger = false
    var draft = ""
    var notice: String?
    var session: Session?
    var relayOnline = false
    var connecting = false
    var sending = false
    var messages: [Message] = []
    var cloudMessages: [Message] = []
    var pins: [Pin] = []
    var snapshot: Snapshot?
    var lastStatusRead: Date?

    private var token = ""
    private var refreshing = false
    private var generation = UUID()
    private var pending: [String: String] = [:]
    private let pinsFile = URL.applicationSupportDirectory.appendingPathComponent("OdinControl/Pins.json")

    var transcript: [Message] { agent == .odin ? messages : cloudMessages }
    var canSend: Bool {
        if agent == .chatGPT { return session?.cloudChatConfigured == true }
        return session?.privateRelayConfigured == true && session?.odinPairingConfigured == true
    }
    var lastReceipt: Date? {
        let bridge = snapshot?.receipts.first(where: { $0.status == "complete" })?.date
        let privateReply = messages.last(where: { $0.sender == "odin" && $0.replyTo != nil })?.date
        return [bridge, privateReply].compactMap { $0 }.max()
    }

    func verifiedReceipt(_ message: Message) -> Bool {
        guard message.sender == "odin", let replyTo = message.replyTo,
              let request = messages.first(where: { $0.id == replyTo && $0.isMine }) else { return false }
        let command = request.text.lowercased().split(whereSeparator: \.isWhitespace).joined(separator: " ")
        switch command {
        case "/status":
            return message.text.hasPrefix("ODIN_STATUS_VERIFIED ")
        case "/task git-status":
            return message.text.hasPrefix("ODIN_TASK_COMPLETE verified=true task=git-status ")
        case "/task queue-status":
            return message.text.hasPrefix("ODIN_TASK_COMPLETE verified=true task=queue-status ")
        case "/restart-services", "/restart-all-services", "restart all services", "restart odin services", "restart odin":
            return message.text.hasPrefix("ODIN_SERVICES_RESTART_RESULT verified=true ")
        default:
            return command.hasPrefix("/restart-service odin-") &&
                message.text.hasPrefix("ODIN_SERVICES_RESTART_RESULT verified=true ")
        }
    }
    var latestHealth: Snapshot.Receipt? {
        snapshot?.receipts.first { $0.action == "odin_health" && $0.status == "complete" }
    }
    var deviceLive: Bool {
        guard let lastReceipt else { return false }
        let age = Date().timeIntervalSince(lastReceipt)
        let checkedRecently = lastStatusRead.map { Date().timeIntervalSince($0) < 75 } ?? false
        return (0...120).contains(age) && (relayOnline || checkedRecently)
    }

    init() {
        if let data = try? Data(contentsOf: pinsFile),
           let saved = try? JSONDecoder().decode([Pin].self, from: data) { pins = saved }
    }

    func restore() async {
        if session == nil, let saved = AccessToken.read() { await connect(saved, remember: false) }
    }

    func connect(_ value: String, remember: Bool) async {
        let candidate = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !connecting, candidate.range(of: #"^[A-Za-z0-9._~-]{32,256}$"#, options: .regularExpression) != nil else {
            notice = "Enter your Odin Control access token."
            return
        }
        connecting = true
        defer { connecting = false }
        do {
            let settings = try await Relay(token: candidate).connect()
            guard settings.authenticated else { throw RelayError.invalidReply }
            generation = UUID()
            token = candidate
            session = settings
            notice = nil
            if remember && !AccessToken.save(candidate) {
                notice = "Connected. The token could not be saved to Keychain."
            }
            await refresh()
        } catch { notice = error.localizedDescription }
    }

    func disconnect() {
        let removed = AccessToken.remove()
        generation = UUID()
        token = ""
        session = nil
        relayOnline = false
        messages = []
        cloudMessages = []
        draft = ""
        pending.removeAll()
        notice = removed ? nil : "Could not remove the saved token from Keychain."
    }

    func refresh() async {
        guard !refreshing else { return }
        refreshing = true
        defer { refreshing = false }
        let current = generation
        let client = Relay(token: token)
        async let status = try? client.status()
        if session?.privateRelayConfigured == true {
            let inbox = try? await client.inbox()
            if current == generation {
                relayOnline = inbox != nil
                if let inbox, inbox.map(\.id) != messages.map(\.id) || inbox.map(\.status) != messages.map(\.status) {
                    messages = inbox
                }
            }
        }
        if let result = await status {
            snapshot = result
            lastStatusRead = Date()
        }
    }

    func send(_ input: String, command: Bool = false) async {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        let target = command ? Agent.odin : agent
        let isReady = target == .odin
            ? session?.privateRelayConfigured == true && session?.odinPairingConfigured == true
            : session?.cloudChatConfigured == true
        guard !text.isEmpty, !sending, isReady else { return }
        let outbound = command ? text : mode.prompt(text, deeper: thinkLonger, agent: target)
        let size = target == .odin ? 1900 : 2800
        guard outbound.utf16.count <= size, outbound.utf8.count <= 4600 else {
            notice = "This message is too long to send."
            return
        }
        sending = true
        notice = nil
        defer { sending = false }
        let current = generation
        let client = Relay(token: token)
        do {
            if target == .odin {
                let id = pending[outbound] ?? UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
                pending[outbound] = id
                try await client.send(outbound, id: id)
                guard current == generation else { return }
                pending.removeValue(forKey: outbound)
                if !messages.contains(where: { $0.id == id }) {
                    messages.append(Message(id: id, at: Date().ISO8601Format(), sender: "iphone",
                                            text: outbound, status: "queued"))
                }
            } else {
                let history = cloudMessages.suffix(8).map { message in
                    Relay.History(role: message.isMine ? "user" : "assistant",
                                  content: String(decoding: message.text.utf16.prefix(2000), as: UTF16.self))
                }
                let answer = try await client.ask(outbound, history: history)
                guard current == generation else { return }
                let now = Date().ISO8601Format()
                cloudMessages += [
                    Message(id: UUID().uuidString, at: now, sender: "iphone", text: outbound, status: ""),
                    Message(id: UUID().uuidString, at: now, sender: "cloud", text: answer, status: "")
                ]
            }
            if !command && draft.trimmingCharacters(in: .whitespacesAndNewlines) == text { draft = "" }
            if target == .odin { await refresh() }
        } catch {
            guard current == generation else { return }
            if target == .odin { notice = "Send unconfirmed. Retry the same message with the same mode. " + error.localizedDescription }
            else { notice = error.localizedDescription }
        }
    }

    func pin(_ text: String, from message: Message, in agent: Agent) {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !pins.contains(where: { $0.messageID == message.id && $0.text == text }) else { return }
        updatePins([Pin(id: UUID(), messageID: message.id, agent: agent.rawValue, text: text)] + pins)
    }

    func unpin(_ pin: Pin) { updatePins(pins.filter { $0.id != pin.id }) }

    private func updatePins(_ value: [Pin]) {
        do {
            try FileManager.default.createDirectory(at: pinsFile.deletingLastPathComponent(), withIntermediateDirectories: true)
            try JSONEncoder().encode(value).write(to: pinsFile, options: [.atomic, .completeFileProtection])
            pins = value
        } catch { notice = "Could not save your pinned items." }
    }
}
