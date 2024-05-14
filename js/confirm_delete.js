function confirmDelete(event) {
    // Mostrar ventana de confirmación
    if (!confirm("¿Estás seguro de que deseas eliminar este bot?")) {
        event.preventDefault(); // Cancelar el envío del formulario si el usuario cancela
    }
}