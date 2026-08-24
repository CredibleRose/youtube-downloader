# YouTube Downloader

Простое окно на Python (tkinter) для скачивания видео и аудио с YouTube через `yt-dlp`.
Без рекламы и без ограничения скорости — работает локально.

## Готовые сборки (Mac / Windows)

Собираются автоматически через GitHub Actions при создании тега `vX.Y.Z` — см.
[.github/workflows/build.yml](.github/workflows/build.yml). Готовые `.zip` с
приложением (внутри — `.app` для Mac или папка с `.exe` для Windows, ffmpeg и
Deno уже вшиты) появляются в разделе **Releases** репозитория.

- **Windows**: скачайте `YouTubeDownloader-windows.zip`, распакуйте, запустите
  `YouTubeDownloader.exe`.
- **Mac (Apple Silicon)**: скачайте `YouTubeDownloader-macos-arm64.zip`.
- **Mac (Intel)**: скачайте `YouTubeDownloader-macos-intel.zip`.

  Распакуйте и перетащите `YouTube Downloader.app` в `Applications`. Так как
  приложение не подписано сертификатом Apple Developer, при первом запуске
  macOS Gatekeeper покажет предупреждение "app is damaged" / "unidentified
  developer". Чтобы разрешить: **правый клик по приложению → Open → Open** в
  диалоге (не двойной клик). Это нужно сделать только один раз.

## Как выпустить новую сборку

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions соберёт Windows и Mac (arm64 + intel) версии и создаст релиз
со всеми файлами автоматически.

## Возможности

- Скачивание видео в mp4 (выбор качества: лучшее / 1080p / 720p / 480p / 360p)
- Извлечение аудио в mp3
- Скачивание целых плейлистов
- Скачивание субтитров (можно указать языки, например `ru,en`)
- Cookies из браузера (Chrome/Edge/Firefox/Brave/Opera/Vivaldi) — обходит
  проверку YouTube "Sign in to confirm you're not a bot"
- Прогрессбар и лог процесса
- Отмена скачивания

## Запуск из исходников (для разработки)

1. Python 3.9+.
2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Установите `ffmpeg` и `deno` (в готовых сборках они уже вшиты, но при
   запуске `python main.py` напрямую их нужно поставить самостоятельно):

   ```bash
   winget install ffmpeg
   winget install DenoLand.Deno
   ```

   После установки перезапустите терминал, чтобы PATH обновился.

4. Запуск:

   ```bash
   python main.py
   ```

## Использование

1. Вставьте ссылку на видео или плейлист.
2. Выберите режим (видео/аудио) и качество.
3. При необходимости включите субтитры, плейлист или cookies из браузера
   (если YouTube просит подтвердить, что вы не бот — для этого закройте
   выбранный браузер перед скачиванием, иначе он может не дать прочитать
   cookies).
4. Выберите папку сохранения (по умолчанию `Видео/YouTube Downloads`).
5. Нажмите «Скачать».

## Заметки

- Программа скачивает только то, на что у вас есть право (например, ваши
  собственные видео или контент с разрешённым скачиванием). Соблюдайте
  условия использования YouTube и авторские права.
- Если YouTube меняет формат сайта, обновите зависимости:

  ```bash
  pip install -U "yt-dlp[default]"
  ```
