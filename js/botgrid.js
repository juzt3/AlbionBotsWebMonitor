const streamEndpoint = '/base64_stream';
let controller = new AbortController(); // Crear un nuevo controlador de aborto

function checkImage(base64string) {
  try {
    const imageData = Uint8Array.from(atob(base64string), c => c.charCodeAt(0));
    return imageData[imageData.length - 2] === 255 && imageData[imageData.length - 1] === 217;
  }
  catch (error) {
    return false;
  }
}

const processStreamData = async (data) => {
  // Procesa los datos recibidos aquí
  const [id, base64_frame] = data.split(':');

  if (checkImage(base64_frame)) {
    const imgElement = document.getElementById(id);
    if (imgElement) {
      imgElement.src = `data:image/jpeg;base64,${base64_frame}`;
    }
  }
};

const consumeStream = async () => {
  const signal = controller.signal; // Obtener la señal del controlador

  try {
    const response = await fetch(streamEndpoint, { signal }); // Pasar la señal al fetch
    let reader = response.body.getReader();
    
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      const chunk = new TextDecoder().decode(value);
      const base64Strings = chunk.split('\n');

      for (const base64String of base64Strings) {
        if (base64String) {
          processStreamData(base64String);
        }
      }
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log('La conexión fue abortada.');
    } else {
      console.error('Error en la lectura del flujo:', error);
    }
  }
};

if (typeof document.hidden !== "undefined") {
  document.addEventListener("visibilitychange", handleVisibilityChange);
}

// Función para manejar el cambio de visibilidad

function handleVisibilityChange() {
  if (!document.hidden || document.visibilityState === 'visible') {
    controller.abort();
    controller = new AbortController();
    consumeStream();
  } else {
    // Detener la conexión cuando se oculta la pestaña o ventana
    controller.abort();
  }
}

window.onload = function() {
  consumeStream();
};
