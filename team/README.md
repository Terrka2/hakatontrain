# Команда проекта
Каждый участник должен создать в этой папке файл со своим именем (например, `ivan.md`), написать внутри свою роль и 1-2 предложения о том, что он делает в этом спринте, затем сделать коммит и пуш.

Работаем по схеме: `feat/* -> dev -> main`. Пушим свою ветку и открываем Pull Request в `dev`.

Пример:
1. git checkout dev && git pull
2. git checkout -b feat/team-ivan
3. echo "Иван, Дата-аналитик. Генерирую синтетику и пишу алгоритм дедупликации." > team/ivan.md
4. git add team/ivan.md
5. git commit -m "feat: add ivan to team"
6. git push origin feat/team-ivan
7. Открыть Pull Request: feat/team-ivan -> dev