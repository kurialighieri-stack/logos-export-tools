# Exportar secciones de Logos a TXT, DOCX y PDF

Herramientas personales para descargar las secciones de los recursos a los que tienes acceso en **tu propia biblioteca de Logos**, usando una sesión iniciada en Logos Web. El proceso no necesita la aplicación de escritorio para extraer el texto.

## Estado y límites

- La extracción por referencia se comprobó en Windows con Romanos completo (21 recursos), Romanos 1–3 (21) e Isaías 33 (15 respuestas con texto, una de ellas solo un encabezado).
- Python genera TXT y DOCX; calibre convierte DOCX a PDF desde código. La implementación portátil de este repositorio se comprobó generando 21 TXT de Romanos 1–3 y un DOCX de Isaías 33 con respuestas locales ya recuperadas. **La ejecución en Pop!_OS y la nueva envoltura portátil de PDF todavía deben verificarse allí**. La instalación portátil anterior de calibre ya no estaba disponible en esta computadora al preparar el repositorio; la conversión original por línea de comandos sí se comprobó con los 21 PDF de Romanos.
- `/api/app/preview` es una ruta interna de Logos Web, no una API pública estable. Puede cambiar, devolver contenido vacío, bloques amplios, solo títulos o una parte del contenido. Una respuesta no garantiza por sí sola la cobertura exhaustiva del pasaje: revisa encabezados y final del TXT.
- Se conserva el bloque que Logos asigna al pasaje; puede incluir capítulos vecinos. No se traducen idiomas. Las imágenes, tablas complejas, notas enlazadas y el diseño original no se reproducen fielmente: se conserva el texto devuelto y formato básico en DOCX.
- No se incluye ningún libro, texto extraído, contraseña, cookie, token ni sesión guardada. Los inventarios de `` son listas de títulos e identificadores; tener un identificador no concede acceso al recurso.

## Instalar en Pop!_OS / Ubuntu

```bash
sudo apt update
sudo apt install git python3 python3-venv calibre
git clone https://github.com/kurialighieri-stack/logos-export-tools.git
cd logos-export-tools
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

El repositorio es privado: autentica GitHub al clonar (GitHub CLI, SSH o tu administrador de credenciales). También puedes descargar **Code → Download ZIP** desde GitHub con sesión iniciada. Para TXT solamente, los scripts usan la biblioteca estándar y no necesitan instalar los paquetes Python de `requirements.txt`.

## 1. Elegir inventario y pasaje

Los inventarios iniciales de esta biblioteca están en `romanos.json` y `isaias.json`. Son candidatos por cobertura del libro; algunos no tienen contenido para todos sus capítulos. Puedes añadir entradas con este formato:

```json
[{"ResourceId": "LLS:29.1.36", "Title": "Comentario de la Biblia Matthew Henry", "Authors": "Henry, Matthew"}]
```

Genera un archivo para el pasaje que quieras:

```bash
python generar_extractor.py --resources romanos.json --reference bible.66.1-66.3 --output extractor.local.js
```

Referencias comprobadas:

| Pasaje | Referencia Logos |
| --- | --- |
| Romanos completo, con introducción cuando está indexada | `bible.66` |
| Romanos 1–3 | `bible.66.1-66.3` |
| Isaías 33 | `bible.23.33` |

**La numeración es la de Logos, no el número de orden de una Biblia de 66 libros**: Romanos se identifica con `66`.

Si conservas una copia del catálogo local de Logos de Windows, puedes regenerar los candidatos en Linux sin instalar Logos:

```bash
python inventario.py --catalog /ruta/catalog.db --book 66 --output inventario.local.json
```

En Windows el archivo suele estar en `%LOCALAPPDATA%\Logos\Data\<perfil>\LibraryCatalog\catalog.db`. Se abre en modo solo lectura. Conviene copiarlo con Logos cerrado; si hay un diario WAL pendiente, una copia aislada puede no reflejar el estado más reciente. El esquema SQLite también puede cambiar. No subas el catálogo a este repositorio.

## 2. Extraer desde tu sesión de navegador

1. Abre <https://app.logos.com/> en Firefox, Chromium o Chrome e inicia sesión personalmente.
2. Abre las herramientas de desarrollo, pestaña **Consola**, en esa misma página.
3. Lee `extractor.local.js` y pega su contenido completo en la consola. Ejecuta solo código que hayas revisado y entiendas; el script trabaja exclusivamente con `app.logos.com`, no envía datos a otro servidor y no lee ni exporta credenciales.
4. Se consultan los recursos secuencialmente, con una pausa de un segundo. Ante HTTP 401/403/429 se detiene el lote: revisa tu sesión o espera antes de reintentar. Un recurso sin texto se registra y no impide continuar con los demás.
5. Al terminar se descarga `Logos - extraccion.zip`, con `json/`, `txt/` y `manifest.json`. Si el navegador bloquea la descarga automática, usa el botón de descarga que aparece en la página. Descomprime el archivo localmente.

La sesión permanece en el perfil de tu navegador mientras Logos la mantenga vigente. No hace falta copiar cookies entre Windows y Linux; inicia sesión una vez en el navegador de Pop!_OS. Si Logos solicita autenticación de nuevo, hazlo directamente allí.

Este paso reemplaza los clics de exportación por libro. El script de consola es una adaptación reutilizable del cliente; la extracción original se comprobó consultando la misma ruta autenticada desde el navegador. Si cambia el comportamiento de la consola o del servicio, revisa `manifest.json` y prueba primero con un recurso y un capítulo.

## 3. Guardar TXT, DOCX y PDF

TXT con nombres de los recursos y comprobación contra el texto original de las respuestas:

```bash
python convertir.py ~/Downloads/Logos/json ~/Documents/Libros/Teologia/Romanos/1-3 --label 'Romanos 1–3'
```

TXT + DOCX:

```bash
python convertir.py ~/Downloads/Logos/json exports/romanos-docx --label 'Romanos 1–3' --docx
```

TXT + DOCX + PDF en la subcarpeta `PDF/`:

```bash
python convertir.py ~/Downloads/Logos/json exports/romanos-pdf --label 'Romanos 1–3' --pdf
```

`--pdf` implica DOCX. Puedes indicar otro ejecutable con `--calibre /ruta/ebook-convert`. Los registros de calibre quedan en `logs/`. No se sustituyen archivos existentes: usa una carpeta nueva al repetir una conversión. Si ocurre un error pueden quedar resultados parciales; revisa el mensaje antes de reintentar.

Los TXT usan UTF-8 con BOM para facilitar su apertura en Windows y Linux. El conversor compara el texto completo del TXT y del DOCX con el XML original, ignorando diferencias de espacio; rechaza texto fuera de párrafos y caracteres de reemplazo. Para PDF comprueba que el archivo pueda abrirse y tenga páginas; **esto no sustituye la revisión de integridad del texto y del diseño del PDF**. En Windows se revisaron además fragmentos iniciales/finales y páginas de muestra de las conversiones originales.

## Privacidad y uso

El control de acceso sigue siendo el de Logos y tu cuenta. No se elimina DRM ni se intenta desbloquear recursos sin acceso. Usa los archivos conforme a tus licencias y no publiques los textos de los libros en GitHub. `.gitignore` ayuda a excluir exportaciones y sesiones, pero revisa siempre lo que añades con Git.
