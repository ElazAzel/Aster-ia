use crate::engine::AudioTranscriber;
use crate::{TranscriptionRequest, TranscriptionResponse, TranscriptionSegment};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};

pub struct WhisperEngine {
    pub model_path: String,
}

impl WhisperEngine {
    pub fn new(model_path: &str) -> Self {
        Self {
            model_path: model_path.to_string(),
        }
    }
}

// A simple helper to read 16kHz WAV mono files and convert to Vec<f32>
fn read_wav(path: &str) -> Result<Vec<f32>, String> {
    let mut file = File::open(path).map_err(|e| format!("Failed to open WAV: {}", e))?;
    let mut header = [0u8; 44];
    file.read_exact(&mut header).map_err(|e| format!("Failed to read WAV header: {}", e))?;

    if &header[0..4] != b"RIFF" || &header[8..12] != b"WAVE" {
        return Err("Not a valid RIFF/WAVE file".to_string());
    }

    // Find the 'data' chunk
    let mut data_chunk_found = false;
    let mut file_len = file.metadata().map_err(|e| e.to_string())?.len();
    file.seek(SeekFrom::Start(12)).map_err(|e| e.to_string())?;

    let mut chunk_header = [0u8; 8];
    let mut sample_rate = 16000;
    let mut channels = 1;
    let mut bits_per_sample = 16;
    let mut format_tag = 1; // 1 = PCM, 3 = Float

    // Read chunks until we find 'data'
    while file.seek(SeekFrom::Current(0)).map_err(|e| e.to_string())? < file_len - 8 {
        file.read_exact(&mut chunk_header).map_err(|e| format!("Failed to read chunk header: {}", e))?;
        let chunk_id = &chunk_header[0..4];
        let chunk_size = u32::from_le_bytes([chunk_header[4], chunk_header[5], chunk_header[6], chunk_header[7]]) as u64;

        if chunk_id == b"fmt " {
            let mut fmt_data = vec![0u8; chunk_size as usize];
            file.read_exact(&mut fmt_data).map_err(|e| e.to_string())?;
            format_tag = u16::from_le_bytes([fmt_data[0], fmt_data[1]]);
            channels = u16::from_le_bytes([fmt_data[2], fmt_data[3]]);
            sample_rate = u32::from_le_bytes([fmt_data[4], fmt_data[5], fmt_data[6], fmt_data[7]]);
            bits_per_sample = u16::from_le_bytes([fmt_data[14], fmt_data[15]]);
        } else if chunk_id == b"data" {
            data_chunk_found = true;
            break;
        } else {
            // Skip this chunk
            file.seek(SeekFrom::Current(chunk_size as i64)).map_err(|e| e.to_string())?;
        }
    }

    if !data_chunk_found {
        return Err("Could not find data chunk in WAV file".to_string());
    }

    if sample_rate != 16000 {
        return Err(format!("Sample rate must be 16000 Hz, got {}", sample_rate));
    }
    if channels != 1 {
        return Err(format!("Channels must be 1 (mono), got {}", channels));
    }

    let mut raw_data = Vec::new();
    file.read_to_end(&mut raw_data).map_err(|e| e.to_string())?;

    let samples = match (format_tag, bits_per_sample) {
        (1, 16) => {
            // 16-bit PCM
            let mut s = Vec::with_capacity(raw_data.len() / 2);
            for chunk in raw_data.chunks_exact(2) {
                let val = i16::from_le_bytes([chunk[0], chunk[1]]);
                s.push(val as f32 / 32768.0);
            }
            s
        }
        (3, 32) => {
            // 32-bit Float
            let mut s = Vec::with_capacity(raw_data.len() / 4);
            for chunk in raw_data.chunks_exact(4) {
                let val = f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
                s.push(val);
            }
            s
        }
        _ => return Err(format!("Unsupported WAV format_tag={} bits_per_sample={}", format_tag, bits_per_sample)),
    };

    Ok(samples)
}

impl AudioTranscriber for WhisperEngine {
    async fn transcribe(&self, req: TranscriptionRequest) -> Result<TranscriptionResponse, String> {
        #[cfg(feature = "native")]
        {
            use whisper_rs::{WhisperContext, WhisperContextParameters, FullParams, SamplingStrategy};

            // 1. Load context parameters and context
            let ctx = WhisperContext::new_with_params(
                &self.model_path,
                WhisperContextParameters::default()
            ).map_err(|e| format!("Failed to load Whisper model: {}", e))?;

            // 2. Load and parse WAV audio data (must be 16kHz mono)
            let audio_data = read_wav(&req.file_path)?;

            // 3. Create state
            let mut state = ctx.create_state().map_err(|e| format!("Failed to create state: {}", e))?;

            // 4. Set parameters
            let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
            if let Some(ref lang) = req.language {
                params.set_language(Some(lang));
            }

            // 5. Execute transcription
            state.full(params, &audio_data[..])
                .map_err(|e| format!("Failed to transcribe: {}", e))?;

            // 6. Gather segments
            let num_segments = state.full_n_segments().map_err(|e| e.to_string())?;
            let mut segments = Vec::new();
            let mut full_text = String::new();

            for i in 0..num_segments {
                let segment_text = state.full_get_segment_text(i).map_err(|e| e.to_string())?;
                let start_time = (state.full_get_segment_t0(i).map_err(|e| e.to_string())? as f32) / 100.0;
                let end_time = (state.full_get_segment_t1(i).map_err(|e| e.to_string())? as f32) / 100.0;

                segments.push(TranscriptionSegment {
                    start: start_time,
                    end: end_time,
                    text: segment_text.clone(),
                });

                if !full_text.is_empty() {
                    full_text.push(' ');
                }
                full_text.push_str(&segment_text);
            }

            let duration = (audio_data.len() as f32) / 16000.0;

            Ok(TranscriptionResponse {
                text: full_text,
                segments,
                language: req.language.unwrap_or_else(|| "ru".to_string()),
                duration,
            })
        }

        #[cfg(not(feature = "native"))]
        {
            // Mock voice transcription
            let segments = vec![
                TranscriptionSegment {
                    start: 0.0,
                    end: 2.0,
                    text: "Тестовая запись голоса в Asterion AI.".to_string(),
                },
                TranscriptionSegment {
                    start: 2.0,
                    end: 5.0,
                    text: "Локальное распознавание работает корректно.".to_string(),
                },
            ];

            let full_text = segments.iter().map(|s| s.text.as_str()).collect::<Vec<_>>().join(" ");

            Ok(TranscriptionResponse {
                text: full_text,
                segments,
                language: req.language.unwrap_or_else(|| "ru".to_string()),
                duration: 5.0,
            })
        }
    }
}
