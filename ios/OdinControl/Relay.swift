import Foundation
import Security

struct Message: Codable, Identifiable {
    let id: String
    let at: String
    let sender: String
    let text: String
    var status: String
    var replyTo: String?
    var failureReason: String?

    var isMine: Bool { sender == "iphone" }
    var date: Date? { parseDate(at) }

}

func parseDate(_ value: String) -> Date? {
    (try? Date.ISO8601FormatStyle(includingFractionalSeconds: true).parse(value)) ??
        (try? Date.ISO8601FormatStyle().parse(value))
}

struct Session: Decodable {
    let authenticated: Bool
    let cloudChatConfigured: Bool
    let privateRelayConfigured: Bool
    let odinPairingConfigured: Bool
}

struct Snapshot: Decodable {
    let receipts: [Receipt]
    struct Receipt: Decodable, Identifiable {
        let id: String
        let action: String
        let status: String
        let checkedAt: String
        let result: Result

        var date: Date? { parseDate(checkedAt) }
        struct Result: Decodable {
            let head: String?
            let queuePending: Int?
            let queueRunning: Int?
            let stage5Reachable: Bool?
        }
    }
}

struct Relay {
    static let origin = "https://odin-control.vercel.app"
    var token: String = ""

    struct Inbox: Decodable { let messages: [Message] }
    struct Delivery: Decodable { let id: String; let status: String }
    struct CloudReply: Decodable { let answer: String }
    struct History: Codable { let role: String; let content: String }
    private struct Empty: Encodable {}
    private struct Send: Encodable { let type = "message"; let text: String; let id: String }
    private struct Cloud: Encodable { let message: String; let history: [History] }

    func connect() async throws -> Session {
        try await request("session", body: Empty())
    }

    func inbox() async throws -> [Message] {
        let result: Inbox = try await get("relay")
        return result.messages
    }

    func status() async throws -> Snapshot { try await get("status") }

    func send(_ text: String, id: String) async throws {
        let confirmation: Delivery = try await request("relay", body: Send(text: text, id: id))
        guard confirmation.id == id, confirmation.status == "queued" else { throw RelayError.invalidReply }
    }

    func ask(_ text: String, history: [History]) async throws -> String {
        let result: CloudReply = try await request("chat", body: Cloud(message: text, history: history))
        return result.answer
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        try await perform(path, body: nil)
    }

    private func request<T: Decodable>(_ path: String, body: some Encodable) async throws -> T {
        try await perform(path, body: JSONEncoder().encode(body))
    }

    private func perform<T: Decodable>(_ path: String, body: Data?) async throws -> T {
        let url = URL(string: Self.origin)!.appendingPathComponent("api").appendingPathComponent(path)
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData,
                                 timeoutInterval: path == "chat" ? 55 : 20)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if path != "status" { request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        if let body {
            request.httpMethod = "POST"
            request.httpBody = body
            request.setValue(Self.origin, forHTTPHeaderField: "Origin")
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw RelayError.invalidReply }
        guard (200..<300).contains(http.statusCode) else { throw RelayError.http(http.statusCode) }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }
}

enum RelayError: LocalizedError {
    case http(Int), invalidReply
    var errorDescription: String? {
        switch self {
        case .http(403): "Private access was rejected. Check your access token."
        case .http(409): "This request ID is already in use."
        case .http(503): "The service is temporarily unavailable."
        case .http(let code): "Odin Control returned HTTP \(code)."
        case .invalidReply: "The server did not confirm the request."
        }
    }
}

enum AccessToken {
    private static let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrService as String: "app.odincontrol.ios",
        kSecAttrAccount as String: "owner-token"
    ]

    static func read() -> String? {
        var item = query
        item[kSecReturnData as String] = true
        item[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(item as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func save(_ token: String) -> Bool {
        let data = Data(token.utf8)
        let changed = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if changed == errSecSuccess { return true }
        guard changed == errSecItemNotFound else { return false }
        var item = query
        item[kSecValueData as String] = data
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        return SecItemAdd(item as CFDictionary, nil) == errSecSuccess
    }

    static func remove() -> Bool {
        let result = SecItemDelete(query as CFDictionary)
        return result == errSecSuccess || result == errSecItemNotFound
    }
}
