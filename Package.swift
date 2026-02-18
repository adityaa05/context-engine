// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "context-agent",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "ContextAgent", targets: ["ContextAgent"])
    ],
    targets: [
        .executableTarget(
            name: "ContextAgent",
            path: "Sources/ContextAgent"
        )
    ]
)
