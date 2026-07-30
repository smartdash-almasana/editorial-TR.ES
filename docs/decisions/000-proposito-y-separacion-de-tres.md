# ADR-000 — Propósito y separación respecto de TRES

**Estado:** Aceptado  
**Fecha:** 2026-07-30

## Contexto

TRES es la aplicación destinada a publicar, distribuir y permitir la lectura de materiales, PDF y futuros app-books.

La producción editorial requiere un sistema independiente para investigar, escribir, revisar, ilustrar, versionar y aprobar obras antes de publicarlas.

## Decisión

Editorial Factory será un repositorio independiente de TRES.

Editorial Factory será responsable de:

- constitución editorial;
- producción literaria;
- géneros;
- voces autorales;
- voces narrativas;
- estilos;
- revisión;
- fuentes;
- infografías;
- láminas;
- ilustraciones;
- preparación de artefactos editoriales;
- generación de paquetes de publicación.

TRES será responsable de:

- recepción de ediciones aprobadas;
- catálogo;
- publicación;
- distribución;
- lectura app-book;
- visualización;
- descarga de artefactos.

## Restricciones

Esta decisión no define todavía:

- stack tecnológico;
- arquitectura de aplicaciones;
- modelo de datos;
- contrato de plugins;
- integración con Vertex AI;
- infraestructura de Google Cloud;
- integración entre ambos repositorios;
- experiencia SaaS.

## Consecuencia

La fórmula editorial interna no deberá formar parte del repositorio de TRES.

TRES recibirá únicamente paquetes editoriales aprobados y preparados para publicación.
