import Foundation
import ImageIO
import UniformTypeIdentifiers

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

if CommandLine.arguments.count != 4 {
    fail("usage: live_photo_metadata <input-jpg> <output-jpg> <asset-id>")
}

let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
let assetID = CommandLine.arguments[3]

guard let source = CGImageSourceCreateWithURL(inputURL as CFURL, nil) else {
    fail("could not open input jpg")
}

guard let uti = CGImageSourceGetType(source) else {
    fail("could not determine input image type")
}

let imageCount = CGImageSourceGetCount(source)
guard imageCount > 0 else {
    fail("input image has no frames")
}

var properties = (CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [String: Any]) ?? [:]
properties[kCGImagePropertyMakerAppleDictionary as String] = ["17": assetID]

guard let destination = CGImageDestinationCreateWithURL(outputURL as CFURL, uti, imageCount, nil) else {
    fail("could not create output jpg")
}

for index in 0..<imageCount {
    let frameProperties: CFDictionary? = index == 0 ? (properties as CFDictionary) : CGImageSourceCopyPropertiesAtIndex(source, index, nil)
    CGImageDestinationAddImageFromSource(destination, source, index, frameProperties)
}

if !CGImageDestinationFinalize(destination) {
    fail("could not finalize output jpg")
}

