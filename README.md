# Telescope Camera Control

Un sistema de control de cámara para telescopios basado en Raspberry Pi utilizando libcamera. Este proyecto permite el control de la cámara, apilamiento de imágenes y opcionalmente control de motores para seguimiento.

## Características

- Captura de imágenes usando libcamera
- Interfaz gráfica intuitiva
- Control de exposición y ganancia
- Apilamiento de imágenes en tiempo real
- Visualización de zoom para enfoque preciso
- Procesamiento de dark frames
- Control de motores opcional para seguimiento (RA/DEC)

## Requisitos de Hardware

- Raspberry Pi (3 o superior recomendado)
- Cámara HQ de Raspberry Pi
- Motores paso a paso (opcional, para seguimiento)
- Controladores de motor (si se usan motores)

## Instalación

1. Clona el repositorio:
```bash
git clone [url-del-repositorio]
cd telescope-camera
```

2. Instala las dependencias del sistema:
```bash
sudo apt-get update
sudo apt-get install -y python3-picamera2 python3-opencv python3-numpy python3-pil
```

3. Instala las dependencias de Python:
```bash
pip install -r requirements.txt
```

## Estructura del Proyecto

```
telescope-camera/
├── main.py              # Aplicación principal
├── camera_control.py    # Control de la cámara
├── motor_control.py     # Control de motores
├── requirements.txt     # Dependencias
├── temp/               # Directorio temporal
└── Pictures/           # Directorio para imágenes guardadas
```

## Uso

### Modo Básico (sin motores)
```bash
python main.py
```

### Con Control de Motores
```bash
python main.py --motors
```

## Características de la Interfaz

### Panel Principal
- Visualización en tiempo real de la imagen de la cámara
- Ventana de zoom para enfoque preciso
- Controles de exposición y ganancia

### Control de Apilamiento
- Apilamiento automático de imágenes
- Control de número máximo de imágenes a apilar
- Guardado de imágenes apiladas
- Visualización de imagen apilada en tiempo real

### Ajustes de Imagen
- Control de brillo y contraste
- Modo umbral para detección de estrellas
- Sustracción de dark frame
- Ajustes de nivel

### Control de Motores (si está habilitado)
- Control de movimiento en RA (Ascensión Recta)
- Control de movimiento en DEC (Declinación)
- Velocidades ajustables
- Modo de seguimiento

## Configuración de GPIO

Si estás utilizando motores, los pines GPIO están configurados de la siguiente manera:

### Motor RA
- GPIO 6
- GPIO 13
- GPIO 19
- GPIO 26

### Motor DEC
- GPIO 12
- GPIO 16
- GPIO 20
- GPIO 21

## Solución de Problemas

### Error de Cámara
Si la cámara no se inicializa:
1. Verifica que la cámara esté correctamente conectada
2. Asegúrate de que la cámara esté habilitada en raspi-config
3. Verifica los permisos de usuario

### Error de Motores
Si los motores no responden:
1. Verifica las conexiones GPIO
2. Asegúrate de que el usuario tenga permisos para GPIO
3. Verifica la alimentación de los motores

## Contribuir

1. Haz un fork del proyecto
2. Crea una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Haz push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## Agradecimientos

- Equipo de libcamera por su excelente biblioteca
- Comunidad de Raspberry Pi
- Contribuidores del proyecto

## Contacto

[Tu Nombre] - [tu@email.com]
Link del proyecto: [url-del-repositorio]
