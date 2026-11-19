import SwiftUI
import UIKit

private let background = Color(red: 7/255, green: 10/255, blue: 18/255)
private let surface = Color(red: 17/255, green: 22/255, blue: 34/255)
private let violet = Color(red: 156/255, green: 141/255, blue: 1)
private let mint = Color(red: 89/255, green: 220/255, blue: 187/255)

@main
struct OdinControlApp: App {
    var body: some Scene {
        WindowGroup { InboxView().preferredColorScheme(.dark).tint(violet) }
    }
}

struct InboxView: View {
    @State private var model = OdinModel()
    @Environment(\.scenePhase) private var scenePhase
    @FocusState private var editing: Bool
    @State private var sidebar = false
    @State private var settings = false
    @State private var restart: String?
    @State private var jump: String?
    @State private var bottomVisible = true

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            ZStack(alignment: .leading) {
                VStack(spacing: 0) {
                    transcript
                    composer
                }
                .accessibilityHidden(sidebar)
                if sidebar {
                    Color.black.opacity(0.64).onTapGesture { sidebar = false }
                        .accessibilityHidden(true)
                    pinsDrawer.transition(.move(edge: .leading))
                }
            }
        }
        .background(background.ignoresSafeArea())
        .sheet(isPresented: $settings) { SettingsView(model: model, restart: requestRestart) }
        .confirmationDialog("Restart Odin services?", isPresented: Binding(
            get: { restart != nil }, set: { if !$0 { restart = nil } }
        ), titleVisibility: .visible, presenting: restart) { command in
            Button("Restart", role: .destructive) {
                restart = nil
                Task { await model.send(command, command: true) }
            }
        } message: { _ in
            Text("This may interrupt active tasks or temporarily disconnect the relay.")
        }
        .task(id: scenePhase) {
            guard scenePhase == .active else { return }
            #if DEBUG
            if ProcessInfo.processInfo.arguments.contains("--layout-test") {
                model.messages = (1...24).map { index in
                    Message(id: String(index), at: "2026-11-19T17:09:00Z",
                            sender: index.isMultiple(of: 2) ? "odin" : "iphone",
                            text: "Sample message \(index). Checking the Odin task queue.",
                            status: "replied")
                }
                return
            }
            #endif
            await model.restore()
            while !Task.isCancelled {
                await model.refresh()
                try? await Task.sleep(for: .seconds(15))
            }
        }
    }

    private var header: some View {
        VStack(spacing: 10) {
            HStack {
                Button {
                    editing = false
                    withAnimation(.easeInOut(duration: 0.18)) { sidebar.toggle() }
                } label: {
                    Image(systemName: "sidebar.left").font(.title3).frame(width: 44, height: 44)
                }
                .accessibilityLabel("Pinned items")
                Spacer()
                Menu {
                    ForEach(Agent.allCases) { option in
                        Button {
                            model.agent = option
                            model.notice = nil
                        } label: {
                            if model.agent == option { Label(option.rawValue, systemImage: "checkmark") }
                            else { Text(option.rawValue) }
                        }
                    }
                } label: {
                    Label(model.agent.rawValue, systemImage: "chevron.down")
                        .labelStyle(AgentLabel()).font(.title3.weight(.semibold))
                }
                .accessibilityLabel("Agent, \(model.agent.rawValue)")
                Spacer()
                Button { editing = false; settings = true } label: {
                    Image(systemName: "gearshape").font(.title3).frame(width: 44, height: 44)
                }
                .accessibilityLabel("Settings")
            }
            StatusStrip(model: model)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 11)
        .frame(maxWidth: .infinity)
        .background(background)
        .accessibilityIdentifier("fixedHeader")
    }

    private var transcript: some View {
        ScrollViewReader { scroll in
            ScrollView {
                if model.transcript.isEmpty {
                    VStack(spacing: 10) {
                        Image(systemName: model.agent == .odin ? "sparkle" : "bubble.left")
                            .font(.system(size: 29)).foregroundStyle(violet)
                        Text(model.agent == .odin ? "Talk to Odin" : "Ask ChatGPT").font(.title2.weight(.semibold))
                        if model.session == nil {
                            Button("Connect in Settings") { settings = true }
                                .buttonStyle(.borderless)
                        } else if model.agent == .chatGPT {
                            Text(model.canSend ? "Uses the OpenAI API" : "Cloud chat is unavailable")
                                .font(.subheadline).foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 65)
                } else {
                    LazyVStack(alignment: .leading, spacing: 19) {
                        ForEach(model.transcript) { message in
                            messageRow(message)
                                .id(message.id)
                        }
                        Color.clear.frame(height: 1).id("bottom")
                            .accessibilityHidden(true)
                            .onAppear { bottomVisible = true }
                            .onDisappear { bottomVisible = false }
                    }
                    .padding(.horizontal, 20).padding(.vertical, 19)
                    .frame(maxWidth: 640)
                    .frame(maxWidth: .infinity)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .defaultScrollAnchor(.bottom, for: .initialOffset)
            .scrollDismissesKeyboard(.interactively)
            .accessibilityIdentifier("transcript")
            .onChange(of: model.agent) {
                bottomVisible = true
                scroll.scrollTo("bottom", anchor: .bottom)
            }
            .onChange(of: model.transcript.last?.id) {
                if bottomVisible || model.transcript.last?.isMine == true {
                    scroll.scrollTo("bottom", anchor: .bottom)
                }
            }
            .onChange(of: jump) {
                if let jump {
                    scroll.scrollTo(jump, anchor: .center)
                    self.jump = nil
                }
            }
        }
    }

    private func messageRow(_ message: Message) -> some View {
        let source = model.agent
        return HStack(alignment: .top, spacing: 10) {
            if message.isMine { Spacer(minLength: 45) }
            else {
                Image(systemName: message.sender == "cloud" ? "bubble.left" : "sparkle")
                    .foregroundStyle(violet).frame(width: 24, height: 25)
                    .accessibilityHidden(true)
            }
            VStack(alignment: message.isMine ? .trailing : .leading, spacing: 6) {
                SelectableMessage(text: message.text, isMine: message.isMine) { selection in
                    model.pin(selection, from: message, in: source)
                }
                if model.verifiedReceipt(message) {
                    Label("Verified on Odin", systemImage: "checkmark.circle.fill")
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(mint)
                        .padding(.horizontal, 8).padding(.vertical, 4)
                        .background(mint.opacity(0.10), in: Capsule())
                } else if message.isMine && !message.status.isEmpty {
                    Text(message.status == "failed" ? "Failed" : message.status.capitalized)
                        .font(.caption2).foregroundStyle(message.status == "failed" ? Color.orange : Color.secondary)
                }
            }
            if !message.isMine { Spacer(minLength: 12) }
        }
        .accessibilityAction(named: Text("Pin message")) {
            model.pin(message.text, from: message, in: source)
        }
    }

    private var composer: some View {
        @Bindable var model = model
        return VStack(alignment: .leading, spacing: 9) {
            if let notice = model.notice {
                HStack(alignment: .top) {
                    Text(notice).font(.caption).foregroundStyle(.orange)
                    Spacer()
                    Button("Dismiss", systemImage: "xmark") { model.notice = nil }
                        .labelStyle(.iconOnly)
                }
            }
            HStack(spacing: 10) {
                Menu {
                    ForEach(Mode.allCases) { option in
                        Button {
                            model.mode = option
                        } label: {
                            if model.mode == option { Label(option.rawValue, systemImage: "checkmark") }
                            else { Text(option.rawValue) }
                        }
                    }
                } label: {
                    Label(model.mode.rawValue, systemImage: "slider.horizontal.3")
                }
                .accessibilityLabel("Mode, \(model.mode.rawValue)")
                Button {
                    model.thinkLonger.toggle()
                } label: {
                    Label("Think longer", systemImage: model.thinkLonger ? "checkmark.circle.fill" : "circle")
                        .foregroundStyle(model.thinkLonger ? violet : .secondary)
                }
                .accessibilityAddTraits(model.thinkLonger ? [.isSelected] : [])
                Spacer()
            }
            .font(.caption.weight(.medium))
            HStack(alignment: .bottom, spacing: 8) {
                TextField(model.agent == .odin ? "Message Odin" : "Ask ChatGPT", text: $model.draft, axis: .vertical)
                    .lineLimit(1...4)
                    .focused($editing)
                    .padding(.vertical, 10)
                    .accessibilityIdentifier("composerInput")
                Button {
                    let draft = model.draft
                    if model.agent == .odin && model.mode != .plan && isRestart(draft) { requestRestart(draft) }
                    else { Task { await model.send(draft) } }
                } label: {
                    Group {
                        if model.sending { ProgressView().tint(background) }
                        else { Image(systemName: "arrow.up").font(.body.weight(.bold)) }
                    }
                    .frame(width: 44, height: 44)
                    .background(violet, in: Circle())
                    .foregroundStyle(background)
                }
                .accessibilityLabel("Send")
                .disabled(!model.canSend || model.sending || model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                .opacity(model.canSend ? 1 : 0.45)
            }
            .padding(.leading, 14).padding(.trailing, 5).padding(.vertical, 4)
            .background(surface, in: RoundedRectangle(cornerRadius: 24))
        }
        .padding(.horizontal, 16).padding(.vertical, 10)
        .frame(maxWidth: 650)
        .frame(maxWidth: .infinity)
        .background(background)
    }

    private var pinsDrawer: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Pinned").font(.title2.weight(.semibold))
                Spacer()
                Button("Close sidebar", systemImage: "xmark") { sidebar = false }
                    .labelStyle(.iconOnly).frame(width: 44, height: 44)
            }
            .padding(16)
            Divider()
            if model.pins.isEmpty {
                Text("Select text in a message, then tap Pin to sidebar.")
                    .font(.subheadline).foregroundStyle(.secondary).padding(18)
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(model.pins) { pin in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(pin.agent).font(.caption.weight(.semibold)).foregroundStyle(violet)
                                Text(pin.text).font(.callout).lineLimit(4).textSelection(.enabled)
                                HStack {
                                    Button("Copy") { UIPasteboard.general.string = pin.text }
                                    Button("Paste to composer") {
                                        model.draft += model.draft.isEmpty ? pin.text : "\n" + pin.text
                                        sidebar = false
                                        editing = true
                                    }
                                }.font(.caption.weight(.semibold))
                                HStack {
                                    if model.transcript.contains(where: { $0.id == pin.messageID }) {
                                        Button("View message") { jump = pin.messageID; sidebar = false }
                                    }
                                    Button("Unpin", role: .destructive) { model.unpin(pin) }
                                }.font(.caption)
                            }
                            .padding(12).frame(maxWidth: .infinity, alignment: .leading)
                            .background(background.opacity(0.7), in: RoundedRectangle(cornerRadius: 12))
                        }
                    }.padding(14)
                }
            }
        }
        .frame(maxWidth: 315, maxHeight: .infinity)
        .background(surface)
        .accessibilityIdentifier("pinsDrawer")
    }

    private func requestRestart(_ text: String) {
        settings = false
        editing = false
        restart = text
    }

    private func isRestart(_ text: String) -> Bool {
        let normalized = text.lowercased().split(whereSeparator: \.isWhitespace).joined(separator: " ")
        return normalized.hasPrefix("/restart") || ["restart all services", "restart odin services", "restart odin"].contains(normalized)
    }
}

private struct AgentLabel: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 6) {
            configuration.title
            configuration.icon.font(.caption.weight(.semibold))
        }
    }
}

private struct StatusStrip: View {
    let model: OdinModel

    var body: some View {
        TimelineView(.periodic(from: .now, by: 15)) { _ in
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 10) { connection; device; Spacer(); lastReceipt }
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 10) { connection; device }
                    lastReceipt
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            .accessibilityIdentifier("connectionStatus")
        }
    }

    private var connection: some View {
        Label(model.relayOnline ? "Relay connected" : model.session == nil ? "Relay locked" : "Relay unavailable",
              systemImage: model.relayOnline ? "link" : "link.badge.plus")
    }

    private var device: some View {
        Label(model.deviceLive ? "Odin live" : "Odin unconfirmed", systemImage: "circle.fill")
            .foregroundStyle(model.deviceLive ? mint : .secondary)
    }

    private var lastReceipt: some View {
        Group {
            if let time = model.lastReceipt {
                HStack(spacing: 3) {
                    Text("Last receipt")
                    Text(time, format: .dateTime.hour().minute().second()).monospacedDigit()
                }
                .accessibilityElement(children: .combine)
                .accessibilityHint(time.formatted(date: .abbreviated, time: .standard))
            } else {
                Text("Last receipt unavailable")
            }
        }
    }
}

private enum Diagnostic: String, CaseIterable {
    case ping = "Ping Odin", queue = "Queue status", git = "Git status", ai = "AI status"
    var command: String {
        switch self {
        case .ping: "/ping"
        case .queue: "/task queue-status"
        case .git: "/task git-status"
        case .ai: "/ai-status"
        }
    }
}

private struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    let model: OdinModel
    let restart: (String) -> Void
    @State private var token = ""
    @State private var remember = true

    var body: some View {
        NavigationStack {
            List {
                Section("Connection") {
                    if model.session == nil {
                        SecureField("Odin Control access token", text: $token)
                            .textContentType(.password).textInputAutocapitalization(.never).autocorrectionDisabled()
                        Toggle("Save to Keychain", isOn: $remember)
                        Button(model.connecting ? "Connecting…" : "Connect") {
                            Task {
                                await model.connect(token, remember: remember)
                                if model.session != nil { token = "" }
                            }
                        }
                        .disabled(token.isEmpty || model.connecting)
                    } else {
                        LabeledContent("Device pairing", value: model.session?.odinPairingConfigured == true ? "Configured" : "Unavailable")
                        LabeledContent("ChatGPT API", value: model.session?.cloudChatConfigured == true ? "Configured" : "Unavailable")
                        Button("Disconnect", role: .destructive) { model.disconnect() }
                    }
                    if let notice = model.notice { Text(notice).font(.footnote).foregroundStyle(.orange) }
                }
                Section("Device") {
                    NavigationLink("Activity & receipts") {
                        List(model.snapshot?.receipts ?? []) { receipt in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(receipt.action.replacingOccurrences(of: "_", with: " ").capitalized)
                                Text(receipt.status.replacingOccurrences(of: "_", with: " ").capitalized)
                                    .font(.caption).foregroundStyle(.secondary)
                                if let date = receipt.date { Text(date.formatted()).font(.caption2).foregroundStyle(.secondary) }
                            }
                        }.navigationTitle("Activity & receipts")
                    }
                    NavigationLink("Diagnostics") {
                        List {
                            if let health = model.latestHealth {
                                if let queue = health.result.queuePending { LabeledContent("Pending tasks", value: String(queue)) }
                                if let queue = health.result.queueRunning { LabeledContent("Running tasks", value: String(queue)) }
                                if let sha = health.result.head { LabeledContent("Device revision", value: String(sha.prefix(8))) }
                                if let date = health.date, let age = health.result.workerHeartbeatAgeS {
                                    LabeledContent("Last worker heartbeat", value: date.addingTimeInterval(-Double(age)).formatted())
                                }
                                if let reachable = health.result.stage5Reachable {
                                    LabeledContent("Stage 5", value: reachable ? "Reachable" : "Unreachable")
                                }
                            }
                            Button("Refresh status") { Task { await model.refresh() } }
                            ForEach(Diagnostic.allCases, id: \.self) { diagnostic in
                                Button(diagnostic.rawValue) {
                                    model.agent = .odin
                                    dismiss()
                                    Task { await model.send(diagnostic.command, command: true) }
                                }
                                .disabled(model.session?.odinPairingConfigured != true)
                            }
                        }.navigationTitle("Diagnostics")
                    }
                    Button("Restart all Odin services", role: .destructive) {
                        dismiss()
                        restart("/restart-services")
                    }.disabled(model.session?.odinPairingConfigured != true)
                }
            }
            .navigationTitle("Settings")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
        .safeAreaInset(edge: .top, spacing: 0) {
            StatusStrip(model: model).padding(12).background(surface)
        }
    }
}

private struct SelectableMessage: UIViewRepresentable {
    let text: String
    let isMine: Bool
    let pin: (String) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(pin: pin) }

    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.delegate = context.coordinator
        view.isEditable = false
        view.isSelectable = true
        view.isScrollEnabled = false
        view.adjustsFontForContentSizeCategory = true
        view.font = .preferredFont(forTextStyle: .body)
        view.textColor = .white
        view.tintColor = UIColor(violet)
        view.backgroundColor = isMine ? UIColor(red: 0.24, green: 0.20, blue: 0.42, alpha: 1) : .clear
        view.layer.cornerRadius = 16
        view.textContainer.lineFragmentPadding = 0
        view.textContainerInset = isMine ? UIEdgeInsets(top: 10, left: 13, bottom: 10, right: 13)
            : UIEdgeInsets(top: 2, left: 0, bottom: 2, right: 0)
        return view
    }

    func updateUIView(_ view: UITextView, context: Context) {
        if view.text != text { view.text = text }
        context.coordinator.pin = pin
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextView, context: Context) -> CGSize? {
        guard let maxWidth = proposal.width, maxWidth > 0 else { return nil }
        let size = uiView.sizeThatFits(CGSize(width: maxWidth, height: .greatestFiniteMagnitude))
        let horizontal = uiView.textContainerInset.left + uiView.textContainerInset.right
        let measured = (text as NSString).size(withAttributes: [.font: uiView.font ?? UIFont.preferredFont(forTextStyle: .body)]).width
        return CGSize(width: min(maxWidth, ceil(measured + horizontal)), height: ceil(size.height))
    }

    final class Coordinator: NSObject, UITextViewDelegate {
        var pin: (String) -> Void
        init(pin: @escaping (String) -> Void) { self.pin = pin }

        func textView(_ textView: UITextView, editMenuForTextIn range: NSRange,
                      suggestedActions: [UIMenuElement]) -> UIMenu? {
            guard range.length > 0, let text = textView.text, let selected = Range(range, in: text) else { return nil }
            let excerpt = String(text[selected])
            let action = UIAction(title: "Pin to sidebar", image: UIImage(systemName: "pin")) { [weak self] _ in
                self?.pin(excerpt)
            }
            return UIMenu(children: suggestedActions + [action])
        }
    }
}
