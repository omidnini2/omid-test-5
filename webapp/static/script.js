"use strict";

const themeSwitch = document.getElementById("themeSwitch");
const voiceInput = document.getElementById("voiceInput");
const recordBtn = document.getElementById("recordBtn");
const stopBtn = document.getElementById("stopBtn");
const recordedPreview = document.getElementById("recordedPreview");
const textInput = document.getElementById("textInput");
const charCount = document.getElementById("charCount");
const submitBtn = document.getElementById("submitBtn");
const downloadSection = document.getElementById("downloadSection");
const downloadLink = document.getElementById("downloadLink");
const outputAudio = document.getElementById("outputAudio");
const langList = document.getElementById("langList");

// Theme handling
themeSwitch.addEventListener("change", () => {
  document.body.classList.toggle("dark", themeSwitch.checked);
  document.body.classList.toggle("light", !themeSwitch.checked);
});

// Character count
textInput.addEventListener("input", () => {
  charCount.textContent = `${textInput.value.length} / 100000`;
});

// Recording with MediaRecorder
let mediaRecorder, audioChunks;
recordBtn.addEventListener("click", async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const url = URL.createObjectURL(blob);
      recordedPreview.src = url;
      recordedPreview.hidden = false;

      // Put blob into File object to mimic upload input
      const file = new File([blob], "recording.webm", { type: "audio/webm" });
      const dt = new DataTransfer();
      dt.items.add(file);
      voiceInput.files = dt.files;
    };

    mediaRecorder.start();
    recordBtn.disabled = true;
    stopBtn.disabled = false;
  } catch (err) {
    alert("اجازه ضبط صدا داده نشد یا خطایی رخ داد.");
  }
});

stopBtn.addEventListener("click", () => {
  mediaRecorder.stop();
  recordBtn.disabled = false;
  stopBtn.disabled = true;
});

// Fetch supported languages
fetch("/api/languages")
  .then((r) => r.json())
  .then((data) => {
    data.languages.forEach((l) => {
      const li = document.createElement("li");
      li.textContent = l;
      langList.appendChild(li);
    });
  });

// Submit generation
submitBtn.addEventListener("click", async () => {
  if (!voiceInput.files.length) {
    alert("لطفاً ابتدا صدای خود را آپلود یا ضبط کنید.");
    return;
  }
  if (!textInput.value.trim()) {
    alert("متن خالی است.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "در حال پردازش...";

  const formData = new FormData();
  formData.append("voice", voiceInput.files[0]);
  formData.append("text", textInput.value);

  try {
    const res = await fetch("/api/clone", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "خطا در سرور");
    }
    const data = await res.json();
    const audioUrl = data.audio_url;
    downloadLink.href = audioUrl;
    outputAudio.src = audioUrl;
    downloadSection.hidden = false;
  } catch (e) {
    alert(`خطا: ${e.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "تولید صدا";
  }
});