const streamEndpoint = '/base64_stream';
let controller = new AbortController();

function checkImage(base64string) {
  try {
    const imageData = Uint8Array.from(atob(base64string), c => c.charCodeAt(0));
    return imageData[imageData.length - 2] === 255 && imageData[imageData.length - 1] === 217;
  } catch (error) {
    return false;
  }
}

async function processStreamData(data) {
  const [id, base64_frame] = data.split(':');
  if (checkImage(base64_frame)) {
    const imgElement = document.getElementById(id);
    if (imgElement) {
      imgElement.src = `data:image/jpeg;base64,${base64_frame}`;
    }
  }
}

async function consumeStream() {
  const signal = controller.signal;

  try {
    const response = await fetch(streamEndpoint, { signal });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const base64Strings = chunk.split('\n');

      for (const base64String of base64Strings) {
        if (base64String) {
          await processStreamData(base64String);
        }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('La conexión fue abortada.');
    } else {
      console.error('Error en la lectura del flujo:', error);
      reconnectStream(); // Intentar reconectar si hay un error
    }
  }
}

function handleVisibilityChange() {
  if (!document.hidden || document.visibilityState === 'visible') {
    controller.abort();
    controller = new AbortController();
    consumeStream();
  } else {
    controller.abort();
  }
}

function reconnectStream() {
  // Esperar antes de intentar reconectar
  setTimeout(() => {
    controller = new AbortController();
    consumeStream();
  }, 5000); // Reintentar después de 5 segundos
}

if (typeof document.hidden !== "undefined") {
  document.addEventListener("visibilitychange", handleVisibilityChange);
}

window.onload = function() {
  consumeStream();
};
