# Orbita

Знакомства по интересам. Пользователь указывает 5–10 тегов, каждый тег переводится в вектор моделью
`paraphrase-multilingual-MiniLM-L12-v2` (384 измерения), профиль — нормированное среднее. Лента сортируется по
косинусной близости, поэтому «бег» и «марафоны» совпадают. Геолокация не используется.

## Запуск

```bash
docker compose up -d --build
docker compose run --rm api python -m scripts.seed demo
```

приложение: http://localhost:8000 
письма (dev): http://localhost:8025


## Остановка
cd ~/Downloads/files/orbita
docker compose down

Проверить, что всё остановлено:
docker compose ps