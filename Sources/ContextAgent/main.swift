import Cocoa
import ApplicationServices
import CoreGraphics
import os.log

let log = OSLog(subsystem: "com.context.agent", category: "sensor")

// MARK: ───────── PERMISSION HELPERS ─────────

func hasAccessibility() -> Bool {
    AXIsProcessTrusted()
}

func requestAccessibility() {
    let options = [kAXTrustedCheckOptionPrompt.takeRetainedValue() as String: true] as CFDictionary
    AXIsProcessTrustedWithOptions(options)
}

func triggerScreenRecording() {
    let rect = CGRect(x: 0, y: 0, width: 10, height: 10)
    _ = CGWindowListCreateImage(rect, .optionOnScreenOnly, kCGNullWindowID, [.bestResolution])
}

// MARK: ───────── SENSOR ─────────

func getFrontmostWindow() -> (String, String) {

    guard let app = NSWorkspace.shared.frontmostApplication else {
        return ("Unknown", "")
    }

    let appName = app.localizedName ?? "Unknown"

    if !hasAccessibility() {
        return (appName, "")
    }

    let pid = app.processIdentifier
    let axApp = AXUIElementCreateApplication(pid)

    var focusedWindow: AnyObject?
    if AXUIElementCopyAttributeValue(axApp, kAXFocusedWindowAttribute as CFString, &focusedWindow) != .success {
        return (appName, "")
    }

    guard let window = focusedWindow else {
        return (appName, "")
    }

    var title: AnyObject?
    AXUIElementCopyAttributeValue(window as! AXUIElement, kAXTitleAttribute as CFString, &title)

    return (appName, title as? String ?? "")
}

func getIdle() -> Double {
    let anyEvent = CGEventType(rawValue: UInt32.max)!
    return CGEventSource.secondsSinceLastEventType(.hidSystemState, eventType: anyEvent)
}

// MARK: ───────── AGENT ─────────

class AgentApp: NSObject, NSApplicationDelegate {

    var permissionTimer: Timer?
    var sensorTimer: Timer?

    var lastApp = ""
    var lastTitle = ""
    var lastIdleBucket = -1

    var screenRecordingRequested = false

    func applicationDidFinishLaunching(_ notification: Notification) {

        print("Agent started")

        // Step 1 — ask accessibility
        requestAccessibility()

        // Step 2 — start permission watcher
        permissionTimer = Timer.scheduledTimer(timeInterval: 1.0, target: self, selector: #selector(checkPermissions), userInfo: nil, repeats: true)
    }

    // MARK: Permission State Machine

    @objc func checkPermissions() {

        if !hasAccessibility() {
            return
        }

        // accessibility granted
        if !screenRecordingRequested {
            print("Accessibility granted → requesting screen recording")
            triggerScreenRecording()
            screenRecordingRequested = true
            return
        }

        // once we can read a real window title → permission granted
        let (_, title) = getFrontmostWindow()
        if !title.isEmpty {

            print("Screen Recording granted → starting sensor")

            permissionTimer?.invalidate()
            permissionTimer = nil

            startSensor()
        }
    }

    // MARK: Sensor

    func startSensor() {

        sensorTimer = Timer.scheduledTimer(timeInterval: 0.25, target: self, selector: #selector(sample), userInfo: nil, repeats: true)
        RunLoop.current.add(sensorTimer!, forMode: .common)
    }

    @objc func sample() {

        let (app, title) = getFrontmostWindow()
        let idle = getIdle()

        let idleBucket = Int(idle / 2)

        if app != lastApp || title != lastTitle || idleBucket != lastIdleBucket {

            lastApp = app
            lastTitle = title
            lastIdleBucket = idleBucket

            let event: [String: Any] = [
                "ts": Date().timeIntervalSince1970,
                "app": app,
                "title": title,
                "idle": idle
            ]

            if let data = try? JSONSerialization.data(withJSONObject: event),
               let json = String(data: data, encoding: .utf8) {

                os_log("%{public}@", log: log, type: .default, json)
            }
        }
    }
}

// MARK: ───────── ENTRY ─────────

let app = NSApplication.shared
let delegate = AgentApp()

app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
