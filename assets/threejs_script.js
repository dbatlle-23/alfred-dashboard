// Este script se cargará automáticamente en Dash desde la carpeta assets
// Esperar a que el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si el contenedor existe
    const container = document.getElementById('threejs-container');
    if (!container) {
        console.error('No se encontró el contenedor para Three.js');
        return;
    }

    // Variables globales
    let scene, camera, renderer, cube;
    
    // Función de inicialización
    function init() {
        // Obtener dimensiones del contenedor
        const width = container.clientWidth;
        const height = container.clientHeight || 500; // Altura por defecto si no está definida
        
        // Crear escena
        scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f0f0);
        
        // Crear cámara
        camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
        camera.position.z = 5;
        
        // Crear renderizador
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(width, height);
        container.appendChild(renderer.domElement);
        
        // Crear geometría (cubo)
        const geometry = new THREE.BoxGeometry(2, 2, 2);
        
        // Crear materiales para cada cara del cubo con colores diferentes
        const materials = [
            new THREE.MeshBasicMaterial({ color: 0xff0000 }), // rojo
            new THREE.MeshBasicMaterial({ color: 0x00ff00 }), // verde
            new THREE.MeshBasicMaterial({ color: 0x0000ff }), // azul
            new THREE.MeshBasicMaterial({ color: 0xffff00 }), // amarillo
            new THREE.MeshBasicMaterial({ color: 0xff00ff }), // magenta
            new THREE.MeshBasicMaterial({ color: 0x00ffff })  // cian
        ];
        
        // Crear cubo con los materiales
        cube = new THREE.Mesh(geometry, materials);
        scene.add(cube);
        
        // Añadir luz ambiental
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        scene.add(ambientLight);
        
        // Añadir luz direccional
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
        directionalLight.position.set(1, 1, 1);
        scene.add(directionalLight);
        
        // Manejar redimensionamiento de ventana
        window.addEventListener('resize', onWindowResize, false);
        
        // Iniciar animación
        animate();
    }
    
    // Función para manejar redimensionamiento
    function onWindowResize() {
        const width = container.clientWidth;
        const height = container.clientHeight || 500;
        
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    }
    
    // Función de animación
    function animate() {
        requestAnimationFrame(animate);
        
        // Rotar el cubo
        cube.rotation.x += 0.01;
        cube.rotation.y += 0.01;
        
        // Renderizar escena
        renderer.render(scene, camera);
    }
    
    // Inicializar Three.js
    init();
}); 