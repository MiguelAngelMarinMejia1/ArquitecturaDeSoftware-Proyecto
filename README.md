# MDJ Hotel

Sistema de gestión de reservas para el Hotel **MDJ**, desarrollado con **Python y Django** como proyecto académico para la asignatura **Arquitectura de Software 2026**.

## Descripción

MDJ Hotel permite gestionar el proceso de creación de reservas mediante una arquitectura desacoplada basada en los principios de **Arquitectura Limpia**, **SOLID** y patrones de diseño creacionales.

La funcionalidad principal implementada es **Crear Reserva**, utilizando una separación por capas entre la interfaz, la lógica de negocio y el dominio.

## Arquitectura

El proyecto se organiza en las siguientes capas:

* **View (CBV):** recibe las solicitudes HTTP.
* **Service Layer:** contiene la lógica del negocio.
* **Builder:** construye y valida objetos `Reserva`.
* **Factory:** crea el servicio de notificación apropiado (real o de desarrollo).

## Tecnologías

* Python 3
* Django
* SQLite
* HTML

## Estructura del taller 1

reserva/

* views.py
* services.py
* models.py
* forms.py
* domain/

  * builders.py
* infra/

  * factories.py
  * notifications.py
* templates/

  * reserva/

## Funcionalidad principal

El flujo de creación de una reserva es el siguiente:

1. El usuario completa el formulario.
2. La vista recibe el request.
3. La vista delega el proceso a `ReservaService`.
4. `ReservaService` utiliza `ReservaBuilder` para validar y construir la reserva.
5. La reserva se almacena en la base de datos.
6. `NotificadorFactory` selecciona el mecanismo de notificación.
7. Se envía la confirmación de la reserva.

## Objetivos académicos

* Aplicar el principio de responsabilidad única.
* Desacoplar la lógica de negocio de las vistas.
* Implementar los patrones **Builder** y **Factory**.
* Demostrar una arquitectura mantenible y extensible.

## Equipo

Proyecto desarrollado para el Taller 01 de Arquitectura de Software 2026.

## Licencia

Proyecto con fines académicos.
