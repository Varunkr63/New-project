const recordButton = document.getElementById("record-btn");
const audioInput = document.getElementById("audio");
const previewAudio = document.getElementById("preview-audio");
const statusLabel = document.getElementById("recording-status");
const voiceEnergyInput = document.getElementById("voice_energy");
const voiceDurationInput = document.getElementById("voice_duration");

if (recordButton) {
  let mediaRecorder;
  let chunks = [];
  let audioContext;
  let analyser;
  let source;
  let stream;
  let levels = [];
  let startedAt = 0;
  let recording = false;

  recordButton.addEventListener("click", async () => {
    if (!recording) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new AudioContext();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      mediaRecorder = new MediaRecorder(stream);
      chunks = [];
      levels = [];
      startedAt = Date.now();

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || "audio/webm" });
        const ext = blob.type.includes("ogg") ? "ogg" : "webm";
        const file = new File([blob], `journal-recording.${ext}`, { type: blob.type });
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
        statusLabel.textContent = `Recording ready • ${voiceDurationInput.value}s • energy ${voiceEnergyInput.value}`;
      };

      mediaRecorder.start();
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
    mediaRecorder.stop();
    stream.getTracks().forEach((track) => track.stop());
    if (audioContext) {
      await audioContext.close();
    }
  });
}
