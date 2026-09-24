Mirror of the speech models Beautiful Voice downloads, so the app works without access to Hugging Face. The files are unchanged copies; `manifest.json` lists each file with its SHA-256 and the repository it came from.

These models are not part of Beautiful Voice and keep their own licenses:

| Model | Authors | License | Source of the files |
|---|---|---|---|
| Nemotron 3.5 ASR Streaming 0.6B | NVIDIA | OpenMDW-1.1 | [csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-int8-2026-06-11](https://huggingface.co/csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-1120ms-int8-2026-06-11) (original: [nvidia/nemotron-3.5-asr-streaming-0.6b](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)) |
| Nemotron Speech Streaming EN 0.6B | NVIDIA | NVIDIA Open Model License | [csukuangfj/sherpa-onnx-nemotron-speech-streaming-en-0.6b-int8-2026-01-14](https://huggingface.co/csukuangfj/sherpa-onnx-nemotron-speech-streaming-en-0.6b-int8-2026-01-14) (original: [nvidia/nemotron-speech-streaming-en-0.6b](https://huggingface.co/nvidia/nemotron-speech-streaming-en-0.6b)) |
| Parakeet TDT 0.6B v3 / v2 | NVIDIA | CC-BY-4.0 | [istupakov/parakeet-tdt-0.6b-v3-onnx](https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx), [istupakov/parakeet-tdt-0.6b-v2-onnx](https://huggingface.co/istupakov/parakeet-tdt-0.6b-v2-onnx) |
| Canary 1B v2 | NVIDIA | CC-BY-4.0 | [istupakov/canary-1b-v2-onnx](https://huggingface.co/istupakov/canary-1b-v2-onnx) |
| GigaAM v3 | Sber (salute-developers) | MIT | [istupakov/gigaam-v3-onnx](https://huggingface.co/istupakov/gigaam-v3-onnx) |
| Whisper Large v3, Large v3 Turbo, Small, Base | OpenAI | MIT | [Systran](https://huggingface.co/Systran) and [mobiuslabsgmbh](https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo) CTranslate2 conversions |
| Distil-Whisper Large v3.5 | Hugging Face | MIT | [distil-whisper/distil-large-v3.5-ct2](https://huggingface.co/distil-whisper/distil-large-v3.5-ct2) |

ONNX exports by [istupakov](https://huggingface.co/istupakov) and the [k2-fsa / sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) project. Files over 2 GB are split into numbered parts; the app joins them and checks the SHA-256.
