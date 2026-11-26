// OCR mit dem Vision-Framework von macOS (lokal, ohne Download).
// Aufruf: ocr_vision <bild1.png> [<bild2.png> ...]  → je Bild eine JSON-Zeile {"datei": ..., "zeilen": [...]}
import AppKit
import Foundation
import Vision

for pfad in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: pfad)
    var zeilen: [String] = []
    if let bild = NSImage(contentsOf: url),
       let cg = bild.cgImage(forProposedRect: nil, context: nil, hints: nil) {
        let anfrage = VNRecognizeTextRequest()
        anfrage.recognitionLevel = .accurate
        anfrage.recognitionLanguages = ["de-DE"]
        // Keine Sprachkorrektur: sie «verbessert» Zahlen und alte Schreibweisen.
        anfrage.usesLanguageCorrection = false
        do {
            try VNImageRequestHandler(cgImage: cg, options: [:]).perform([anfrage])
            for beobachtung in anfrage.results ?? [] {
                if let kandidat = beobachtung.topCandidates(1).first { zeilen.append(kandidat.string) }
            }
        } catch {
            FileHandle.standardError.write("Fehler \(pfad): \(error)\n".data(using: .utf8)!)
        }
    }
    let daten = try! JSONSerialization.data(withJSONObject: ["datei": pfad, "zeilen": zeilen])
    print(String(data: daten, encoding: .utf8)!)
}
