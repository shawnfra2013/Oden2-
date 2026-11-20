# Odin Control for iPhone

Native SwiftUI app for iOS 18 or newer. The header shows relay connection,
recent device activity, and the last receipt time. The transcript scrolls
between the header and composer. Settings contains pairing, activity,
diagnostics, and confirmed service controls.

Choose Odin or ChatGPT with the agent picker. Start, Plan, and Work change
the guidance sent with a question. Think longer asks for additional analysis
in the prompt. ChatGPT is the project's OpenAI API conversation. In Start
and Work, slash commands go to Odin unchanged through the private relay.
Plan mode asks for planning help and routes typed slash commands as text.

Long-press within a message to select text. Copy uses the native selection
menu. Pin to sidebar saves the selected excerpt on this iPhone. The sidebar
can copy an excerpt or insert it into the composer. The composer supports
standard iOS paste and editing. The app saves the access token to Keychain
if selected during connection.

Generate the project on a Mac with Xcode and XcodeGen:

```sh
cd ios
xcodegen generate
open OdinControl.xcodeproj
```

Choose the OdinControl scheme and an iPhone simulator. To run on a physical
iPhone, use your development signing team in Xcode. Use your existing Odin
Control owner token in Settings. The simulator layout test uses sample
messages and does not need credentials.
