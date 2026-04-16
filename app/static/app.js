const recordButton = document.getElementById("record-btn");
const audioInput = document.getElementById("audio");
const previewAudio = document.getElementById("preview-audio");
const statusLabel = document.getElementById("recording-status");
const voiceEnergyInput = document.getElementById("voice_energy");
const voiceDurationInput = document.getElementById("voice_duration");

if (recordButton) {
  let audioContext;
  let analyser;
  let source;
  let stream;
  let levels = [];
  let startedAt = 0;
  let recording = false;
  let processor;
  let pcmChunks = [];

  recordButton.addEventListener("click", async () => {
    if (!recording) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new AudioContext();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      pcmChunks = [];
      levels = [];
      startedAt = Date.now();
      source.connect(processor);
      processor.connect(audioContext.destination);
      processor.onaudioprocess = (event) => {
        if (!recording) {
          return;
        }
        pcmChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };

      recording = true;
      recordButton.textContent = "Stop recording";
      statusLabel.textContent = "Recording in progress...";

      const sampleLevel = () => {
        if (!recording || !analyser) {
          return;
        }
        const buffer = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteTimeDomainData(buffer);
        let total = 0;
        for (let i = 0; i < buffer.length; i += 1) {
          const normalized = (buffer[i] - 128) / 128;
          total += normalized * normalized;
        }
        levels.push(Math.min(Math.sqrt(total / buffer.length) * 3, 1));
        requestAnimationFrame(sampleLevel);
      };

      requestAnimationFrame(sampleLevel);
      return;
    }

    recording = false;
    recordButton.textContent = "Start recording";
    processor.disconnect();
    source.disconnect(processor);
    stream.getTracks().forEach((track) => track.stop());
    const blob = encodeWav(pcmChunks, audioContext.sampleRate);
    const file = new File([blob], "journal-recording.wav", { type: "audio/wav" });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    audioInput.files = transfer.files;

    previewAudio.src = URL.createObjectURL(blob);
    previewAudio.classList.remove("hidden");
    voiceDurationInput.value = ((Date.now() - startedAt) / 1000).toFixed(1);
    const averageLevel = levels.length
      ? levels.reduce((sum, value) => sum + value, 0) / levels.length
      : 0;
    voiceEnergyInput.value = averageLevel.toFixed(3);
    statusLabel.textContent = `Recording ready | ${voiceDurationInput.value}s | energy ${voiceEnergyInput.value}`;
    if (audioContext) {
      await audioContext.close();
    }
  });
}

function encodeWav(chunks, sampleRate) {
  const samples = mergeChunks(chunks);
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, "WAVE");
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

function mergeChunks(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Float32Array(totalLength);
  let offset = 0;
  chunks.forEach((chunk) => {
    result.set(chunk, offset);
    offset += chunk.length;
  });
  return result;
}

function writeString(view, offset, value) {
  for (let i = 0; i < value.length; i += 1) {
    view.setUint8(offset + i, value.charCodeAt(i));
  }
}
