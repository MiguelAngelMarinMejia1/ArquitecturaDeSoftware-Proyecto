# Fotos del sitio

Coloca aquí las fotos con **estos nombres exactos**. La hoja de estilos
(`web/static/web/css/mdj.css`, sección "Photo slots") las carga sola; si falta
alguna, se ve la composición dibujada en CSS y no una imagen rota.

| Archivo          | Dónde aparece                                         | Tamaño sugerido |
|------------------|-------------------------------------------------------|-----------------|
| `hero.jpg`       | Portada (pantalla completa) y galería                 | 1920 × 1080     |
| `hotel.jpg`      | Sección "El hotel" y galería                          | 1600 × 1000     |
| `habitacion.jpg` | Tarjetas de habitaciones sin foto propia y galería    | 1200 × 900      |
| `ciudad.jpg`     | Sección "Experiencia y ubicación" y galería           | 1600 × 1000     |

- Formato JPG, calidad ~75-80 %, idealmente menos de 400 KB cada una.
- La portada lleva texto blanco encima con un degradado oscuro: funcionan mejor
  fotos con el sujeto a la derecha.
- Después de agregarlas: `docker compose up -d --build django_web`.
