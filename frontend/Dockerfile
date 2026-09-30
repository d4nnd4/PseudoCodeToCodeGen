# Etapa 1: descarga Monaco Editor desde npm para servirlo localmente (sin CDN u otros añadidos).
# Ignorar mensajes de vulnerabilidad de Docker
FROM node:22-alpine AS monaco
WORKDIR /tmp/m
RUN npm pack monaco-editor@0.52.2 --silent && tar -xzf monaco-editor-*.tgz

# Etapa 2: Nginx sirve el frontend y hace proxy de /api al backend.
# Ignorar mensajes de vulnerabilidad de Docker
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=monaco /tmp/m/package/min/vs /usr/share/nginx/html/vendor/monaco/vs
COPY index.html styles.css app.js rpgle.js /usr/share/nginx/html/
