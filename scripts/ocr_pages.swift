// OCR scanned page images with the macOS Vision framework, entirely on this machine.
//
// Usage: swift scripts/ocr_pages.swift page-01.png page-02.png ... > out.txt
//
// Each image is printed after a "〔PDF 第 N 页〕" line, N counting the images in
// the order given. Wide images are treated as two-page spreads: they are cut
// in half and the left page is read first. Sideways text, such as rotated
// running heads, is skipped. Render the PDF at 300 dpi first, for example:
//   pdftoppm -r 300 -png scan.pdf out/page
// A blank line marks a new paragraph, found from larger vertical gaps and
// from first-line indents.

import AppKit
import Foundation
import Vision

struct Piece {
    let text: String
    let minX: Double, maxX: Double, minY: Double, maxY: Double
    var midY: Double { (minY + maxY) / 2 }
    var height: Double { maxY - minY }
}

struct Line {
    var text: String
    var minX: Double, minY: Double, maxY: Double
}

func load(_ path: String) throws -> CGImage {
    guard let image = NSImage(contentsOfFile: path),
          let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        throw NSError(domain: "ocr", code: 1, userInfo: [NSLocalizedDescriptionKey: "cannot read \(path)"])
    }
    return cg
}

/// Find the gutter of a spread: the band with the least ink in the middle 30-70% of the width.
func gutter(of cg: CGImage) -> Int {
    let width = cg.width, height = cg.height
    var pixels = [UInt8](repeating: 255, count: width * height)
    let space = CGColorSpaceCreateDeviceGray()
    pixels.withUnsafeMutableBytes { buffer in
        if let ctx = CGContext(data: buffer.baseAddress, width: width, height: height, bitsPerComponent: 8,
                               bytesPerRow: width, space: space, bitmapInfo: CGImageAlphaInfo.none.rawValue) {
            ctx.draw(cg, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
    }
    var ink = [Int](repeating: 0, count: width)
    for y in stride(from: 0, to: height, by: 2) {
        let row = y * width
        for x in 0..<width where pixels[row + x] < 128 {
            ink[x] += 1
        }
    }
    let window = max(width / 100, 4)
    var best = width / 2, bestInk = Int.max
    for x in (width * 3 / 10)..<(width * 7 / 10 - window) {
        let sum = ink[x..<(x + window)].reduce(0, +)
        if sum < bestInk {
            bestInk = sum
            best = x + window / 2
        }
    }
    return best
}

/// A two-page spread is cut at its gutter, so each page is recognised on its
/// own; recognising the whole spread at once drops lines.
func pages(of cg: CGImage) -> [CGImage] {
    guard cg.width > cg.height else { return [cg] }
    let cut = gutter(of: cg)
    let left = cg.cropping(to: CGRect(x: 0, y: 0, width: cut, height: cg.height))
    let right = cg.cropping(to: CGRect(x: cut, y: 0, width: cg.width - cut, height: cg.height))
    return [left, right].compactMap { $0 }
}

func recognise(_ cg: CGImage) throws -> [Piece] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-US"]
    try VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])
    var pieces: [Piece] = []
    for observation in request.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        if box.height > box.width { continue }  // sideways text
        pieces.append(Piece(text: candidate.string, minX: box.minX, maxX: box.maxX, minY: box.minY, maxY: box.maxY))
    }
    return pieces
}

func median(_ values: [Double]) -> Double {
    let sorted = values.sorted()
    return sorted.isEmpty ? 0.01 : sorted[sorted.count / 2]
}

/// Merge pieces that sit on the same visual line, then order lines top to bottom.
func lines(of pieces: [Piece]) -> [Line] {
    let h = median(pieces.map { $0.height })
    var result: [Line] = []
    var current: [Piece] = []
    func flush() {
        guard !current.isEmpty else { return }
        let ordered = current.sorted { $0.minX < $1.minX }
        result.append(Line(
            text: ordered.map { $0.text }.joined(separator: " "),
            minX: ordered[0].minX,
            minY: ordered.map { $0.minY }.min()!,
            maxY: ordered.map { $0.maxY }.max()!
        ))
        current = []
    }
    for piece in pieces.sorted(by: { $0.midY > $1.midY }) {
        if let first = current.first, abs(first.midY - piece.midY) > h / 2 {
            flush()
        }
        current.append(piece)
    }
    flush()
    return result
}

/// Join lines into paragraphs separated by blank lines.
func paragraphs(_ lines: [Line]) -> String {
    guard !lines.isEmpty else { return "" }
    let h = median(lines.map { $0.maxY - $0.minY })
    let margin = lines.map { $0.minX }.sorted()[lines.count / 10]
    let indent = 0.012
    var out = lines[0].text
    for i in 1..<lines.count {
        let prev = lines[i - 1], cur = lines[i]
        let gap = prev.minY - cur.maxY
        let curIndent = cur.minX - margin
        let prevIndent = prev.minX - margin
        let newPara = gap > 0.6 * h || (curIndent > indent && curIndent - prevIndent > indent)
        out += (newPara ? "\n\n" : "\n") + cur.text
    }
    return out
}

var pageNumber = 0
for path in CommandLine.arguments.dropFirst() {
    pageNumber += 1
    do {
        print("〔PDF 第 \(pageNumber) 页〕\n")
        for page in pages(of: try load(path)) {
            let pieces = try recognise(page)
            if !pieces.isEmpty {
                print(paragraphs(lines(of: pieces)))
                print("")
            }
        }
    } catch {
        FileHandle.standardError.write("\(error.localizedDescription)\n".data(using: .utf8)!)
        exit(1)
    }
}
