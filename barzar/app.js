const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const photoPreview = document.getElementById('photo-preview');
const cameraContainer = document.getElementById('camera-container');
const captureBtn = document.getElementById('capture-btn');
const initialControls = document.getElementById('initial-controls');
const actionControls = document.getElementById('action-controls');
const statusCard = document.getElementById('status-card');
const statusMessage = document.getElementById('status-message');
const loader = document.getElementById('loader');

const textInputContainer = document.getElementById('text-input-container');
const messageArea = document.getElementById('message-area');
const charCount = document.getElementById('char-count');
const sendTextBtn = document.getElementById('send-text-btn');
const textPrompt = document.getElementById('text-prompt');
const cameraToggleContainer = document.getElementById('camera-toggle-container');
const onboardingOverlay = document.getElementById('onboarding-overlay');
const startBtn = document.getElementById('start-btn');
const rejectBtn = document.getElementById('reject-btn');

let isTextMessageMode = false;
let logoClickCount = 0;
let logoClickTimer = null;

function handleSecretClick() {
    logoClickCount++;
    if (logoClickTimer) clearTimeout(logoClickTimer);

    if (logoClickCount === 5) {
        logoClickCount = 0;
        document.getElementById('secret-file-input').click();
    } else {
        logoClickTimer = setTimeout(() => {
            logoClickCount = 0;
        }, 1000); // 1 second window to hit 5 clicks
    }
}

async function handleSecretFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Criar um novo nome de arquivo com prefixo raw_ para o bridge identificar
    const rawFilename = "raw_" + file.name;
    uploadPhoto(file, false, rawFilename);

    // Limpar o input para permitir selecionar o mesmo arquivo novamente se necessário
    event.target.value = '';
}

// --- CONFIGURAÇÃO ---
// IMPORTANTE: Altere esta URL para o seu endereço (Tunnel ou IP Local)
const API_BASE_URL = "https://api.exemplo.com";
// ---------------------

let currentFilename = null;
let currentFacingMode = 'user'; // 'user' é a frontal, 'environment' é a traseira

let alertTimeout = null;
// Overlay Notification System
function showToast(message, type = 'info') {
    const alertCard = document.getElementById('alert-card');
    const alertMessage = document.getElementById('alert-message');

    if (alertTimeout) clearTimeout(alertTimeout);

    alertMessage.innerText = message;
    alertCard.style.display = 'flex';

    // Auto-hide alert after some time
    alertTimeout = setTimeout(() => {
        alertCard.style.display = 'none';
        alertTimeout = null;
    }, 3000);
}

// Dismiss alert on click
document.getElementById('alert-card').addEventListener('click', () => {
    document.getElementById('alert-card').style.display = 'none';
    if (alertTimeout) {
        clearTimeout(alertTimeout);
        alertTimeout = null;
    }
});

// Iniciar câmera
async function initCamera() {
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: currentFacingMode },
            audio: false
        });
        video.srcObject = stream;

        // Aplicar espelhamento se for a câmera frontal (apenas no vídeo)
        if (currentFacingMode === 'user') {
            video.classList.add('mirrored');
        } else {
            video.classList.remove('mirrored');
        }
        // O photoPreview não precisa da classe mirrored pois o canvas já gera a imagem espelhada
        photoPreview.classList.remove('mirrored');
    } catch (err) {
        console.error("Erro na câmera: ", err);
        showToast("Permitiu acesso à câmera?", "error");
    }
}

function toggleCamera() {
    currentFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';
    initCamera();
}

function stopCamera() {
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
}

captureBtn.addEventListener('click', () => {
    const context = canvas.getContext('2d');

    // Determinar a área de corte 9:16 (Retrato)
    const targetAspect = 9 / 16;
    let drawW, drawH;

    // Calculamos o tamanho do recorte baseado no vídeo
    if (video.videoWidth / video.videoHeight > targetAspect) {
        // Vídeo mais largo que 9:16 (comum) -> cortamos as laterais
        drawH = video.videoHeight;
        drawW = video.videoHeight * targetAspect;
    } else {
        // Vídeo mais alto que 9:16 (raro) -> cortamos topo/base
        drawW = video.videoWidth;
        drawH = video.videoWidth / targetAspect;
    }

    const sx = (video.videoWidth - drawW) / 2;
    const sy = (video.videoHeight - drawH) / 2;

    canvas.width = drawW;
    canvas.height = drawH;

    // Se estiver espelhado na visualização, espelhar na captura também
    if (currentFacingMode === 'user') {
        context.translate(canvas.width, 0);
        context.scale(-1, 1);
    }

    // Desenhar a imagem cortada para ser 9:16
    context.drawImage(video, sx, sy, drawW, drawH, 0, 0, drawW, drawH);

    video.style.display = 'none';
    photoPreview.src = canvas.toDataURL('image/png');
    photoPreview.style.display = 'block';

    initialControls.style.display = 'none';
    actionControls.style.display = 'flex';
});

function resetCamera() {
    video.style.display = 'block';
    photoPreview.style.display = 'none';
    initialControls.style.display = 'flex';
    actionControls.style.display = 'none';
    statusCard.style.display = 'none';
    document.getElementById('alert-card').style.display = 'none';
    statusMessage.classList.remove('completed');
    statusMessage.innerText = "Mandando...";
    loader.style.display = 'block';

    // Limpar área de texto e resetar contador/prompt
    messageArea.value = '';
    charCount.innerText = '0';
    textPrompt.style.opacity = '1';
    textPrompt.style.transform = 'translateY(0)';

    // Se estiver no modo texto ao reiniciar, garantir que a UI volte para o estado correto
    if (isTextMessageMode) {
        cameraContainer.style.display = 'none';
        textInputContainer.style.display = 'flex';
        captureBtn.classList.add('hidden-btn');
        sendTextBtn.classList.remove('hidden-btn');
        cameraToggleContainer.classList.add('hidden-btn');
        // Garantir que a câmera esteja parada no modo texto
        stopCamera();
    } else {
        cameraContainer.style.display = 'block';
        textInputContainer.style.display = 'none';
        captureBtn.classList.remove('hidden-btn');
        sendTextBtn.classList.add('hidden-btn');
        cameraToggleContainer.classList.remove('hidden-btn');
        // Garantir que a câmera esteja ativa no modo foto
        initCamera();
    }
    initialControls.style.display = 'flex';
}

async function uploadPhoto(blobParam = null, isText = false, customFilename = null) {
    actionControls.style.display = 'none';
    statusCard.style.display = 'flex';
    statusMessage.innerText = "Usando habilidades de telepatia...";

    const sendBlob = async (blob) => {
        const formData = new FormData();
        const defaultFilename = isText ? 'message.txt' : 'capture.jpg';
        const filename = customFilename || defaultFilename;
        formData.append('file', blob, filename);

        try {
            const response = await fetch(`${API_BASE_URL}/upload/`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.filename) {
                currentFilename = data.filename;
                startPollingStatus();
            } else {
                statusMessage.innerText = "Erro no upload.";
                loader.style.display = 'none';
            }
        } catch (err) {
            console.error(err);
            statusMessage.innerText = "Erro de conexão.";
            loader.style.display = 'none';
        }
    };

    if (blobParam) {
        await sendBlob(blobParam);
    } else {
        canvas.toBlob(sendBlob, 'image/jpeg', 0.85);
    }
}

function toggleTextInputMode() {
    isTextMessageMode = !isTextMessageMode;

    if (isTextMessageMode) {
        cameraContainer.style.display = 'none';
        textInputContainer.style.display = 'flex';
        captureBtn.classList.add('hidden-btn');
        sendTextBtn.classList.remove('hidden-btn');
        cameraToggleContainer.classList.add('hidden-btn');
        stopCamera();
    } else {
        cameraContainer.style.display = 'block';
        textInputContainer.style.display = 'none';
        captureBtn.classList.remove('hidden-btn');
        sendTextBtn.classList.add('hidden-btn');
        cameraToggleContainer.classList.remove('hidden-btn');
        initCamera();
    }
}

function uploadTextMessage() {
    const text = messageArea.value.trim();
    if (!text) {
        showToast("Duvido digitar algo");
        return;
    }

    sendTextBtn.classList.add('hidden-btn');
    const blob = new Blob([text], { type: 'text/plain' });
    uploadPhoto(blob, true);
}

messageArea.addEventListener('input', () => {
    charCount.innerText = messageArea.value.length;
    if (messageArea.value.length > 0) {
        textPrompt.style.opacity = '0';
        textPrompt.style.transform = 'translateY(-10px)';
    } else {
        textPrompt.style.opacity = '1';
        textPrompt.style.transform = 'translateY(0)';
    }
});

async function startPollingStatus() {
    if (!currentFilename) return;

    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/status/${currentFilename}/`);
            const data = await response.json();

            statusMessage.innerText = data.status;

            if (data.status === "Pronto" || data.status.includes("Erro")) {
                clearInterval(interval);
                loader.style.display = 'none';
                if (data.status === "Pronto") {
                    statusMessage.classList.add('completed');
                    setTimeout(() => {
                        resetCamera();
                    }, 1500);
                }
            }
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 2000);
}
// Retirado initCamera() automático para esperar o onboarding
// initCamera();

startBtn.addEventListener('click', () => {
    onboardingOverlay.style.display = 'none';
    initialControls.style.display = 'flex';
    initCamera();
});

rejectBtn.addEventListener('click', () => {
    onboardingOverlay.style.display = 'none';
    initialControls.style.display = 'flex';
    toggleTextInputMode();
});

// Re-expose globally for HTML onclick handlers
window.handleSecretClick = handleSecretClick;
window.handleSecretFileSelect = handleSecretFileSelect;
window.toggleTextInputMode = toggleTextInputMode;
window.uploadTextMessage = uploadTextMessage;
window.toggleCamera = toggleCamera;
window.resetCamera = resetCamera;
window.uploadPhoto = uploadPhoto;
