# Контракт disposable QA-ресурсов aiplanner (AP-020)

Область: локальный API pytest harness; без production side effects.

- Тестовая SQLite существует только в памяти процесса. `StaticPool` разделяет
  одну connection с потоками TestClient; существующая SessionLocal привязывается
  к этому engine до импорта routers. Production database module не меняется.
- Engine имеет metadata `owner=aiplanner`, `project=aiplanner`, уникальный `run`,
  `purpose=api-tests`, UTC `expiry` (15 минут). Это идентификация QA, не таймер.
- Fixture закрывает sessions и удаляет таблицы в finally; завершение pytest
  освобождает engine. При SIGTERM/SIGKILL и hard crash память освобождает ОС:
  durable DB, volumes и отдельный DB-процесс не создаются. Поэтому следующему
  запуску нечего удалять по expiry; sweeper/таймер не добавляется.
- `tools/qa/check_api_resources.py` запускает только synthetic probe с bounded
  readiness/wait/termination, отдельной process group, cleanup в finally и
  обработкой SIGINT/SIGTERM supervisor. Ready handshake использует pipe, не файл.
  Логи child подавлены; evidence — только ограниченный JSON manifest в stdout.
- Probe проверяет shared in-memory connection и ownership/expiry до readiness.
  Success/failure/timeout/SIGINT/SIGTERM/SIGKILL и следующий запуск проверяют RC,
  отсутствие новых owned volumes/контейнеров, orphan process groups и DB-файлов.
  Docker используется только для чтения количества и сравнения resource IDs;
  Ownership фильтр: `qa.owner=aiplanner`, `qa.project=aiplanner`, `qa.run=<uuid>`.
  Общий inventory отображается только численно: параллельные чужие allocations
  не приписываются этому запуску. IDs, process env, логи, секреты и
  пользовательские данные не выводятся.
- В репозитории нет disposable PostgreSQL/Compose QA harness. Ручные migration
  и restore drills не являются разрешением очищать рабочие БД. Новый durable
  harness обязан до allocation задать labels `qa.owner`, `qa.project`, `qa.run`,
  `qa.purpose`, `qa.expiry`,
  удалить exact owned resources при любом завершении и на следующем запуске
  точечно проверить просроченные labels после hard crash. `docker rm -fv`
  допустим только для owned disposable container; Compose down --volumes —
  только для exact owned synthetic project. Global prune запрещён.
- Постоянные PostgreSQL/Redis/Caddy данные и dormant optional Caddy profile
  не входят в QA cleanup; отсутствие пустых dormant volumes не является ошибкой.

Проверка: `.venv/bin/python -B tools/qa/check_api_resources.py` из корня проекта.
Требуются dev-зависимости API и read-only доступ к Docker inventory. Ошибка
readiness/Docker/RC или ненулевой прирост owned ресурсов означает nonzero checker RC.
