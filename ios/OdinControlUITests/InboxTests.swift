import XCTest

final class InboxTests: XCTestCase {
    func testTranscriptScrollKeepsHeaderAndComposerFixed() {
        let app = XCUIApplication()
        app.launchArguments = ["--layout-test"]
        app.launch()

        let transcript = app.scrollViews["transcript"]
        XCTAssertTrue(transcript.waitForExistence(timeout: 8))
        let sidebar = app.buttons["Pinned items"]
        let composer = app.descendants(matching: .any)["composerInput"].firstMatch
        XCTAssertTrue(sidebar.exists)
        XCTAssertTrue(composer.exists)
        let headerFrame = sidebar.frame
        let composerFrame = composer.frame
        let inbox = XCTAttachment(screenshot: app.screenshot())
        inbox.name = "Odin inbox"
        inbox.lifetime = .keepAlways
        add(inbox)
        transcript.swipeDown()
        XCTAssertEqual(sidebar.frame, headerFrame)
        XCTAssertEqual(composer.frame, composerFrame)
        XCTAssertTrue(app.staticTexts["Last receipt unavailable"].exists)

        sidebar.tap()
        XCTAssertTrue(app.staticTexts["Pinned"].waitForExistence(timeout: 4))
        let pins = XCTAttachment(screenshot: app.screenshot())
        pins.name = "Pinned sidebar"
        pins.lifetime = .keepAlways
        add(pins)
    }
}
