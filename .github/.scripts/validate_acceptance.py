#!/usr/bin/env python3
import os
import sys
import yaml
from pathlib import Path
import subprocess


REFERENCE_AGREEMENT = """Я подтверждаю следующее:
1. Я не буду списывать решения у других участников курса.
2. При использовании больших языковых моделей (LLM) или других генеративных ИИ-инструментов
   для выполнения домашних заданий я обязуюсь полностью понимать присланный код и быть
   готовым пояснить, как он работает, почему используется та или иная конструкция,
   а также внести в него изменения по запросу преподавателя.

Нарушение этих правил может повлечь за собой исключение из курса или аннулирование результатов.
"""


def load_env_vars():
    return {
        'pr_title': os.environ.get('PR_TITLE', '').strip(),
        'pr_branch': os.environ.get('PR_HEAD_REF', '').strip(),
        'pr_author': os.environ.get('PR_AUTHOR', '').strip(),
        'base_sha': os.environ.get('BASE_SHA', '').strip(),
        'head_sha': os.environ.get('HEAD_SHA', '').strip(),
    }


def print_header(pr_author):
    print("=" * 70)
    print("Валидация регистрации на курс FBB Orchestration 2025")
    print(f"\tАвтор PR (эталонный username): {pr_author}")
    print("=" * 70)
    print()


def validate_branch_name(pr_author, pr_branch):
    errors = []
    expected = f"{pr_author}_accept"
    if pr_branch != expected:
        errors.append(
            f"!!  Неверное имя ветки.\n"
            f"    Ожидается: '{expected}'\n"
            f"    Получено:  '{pr_branch}'\n"
        )
    else:
        print(f"....Ветка имеет корректное имя: {pr_branch}")
    return errors


def validate_pr_title(pr_author, pr_title):
    errors = []
    expected = f"acceptance-orch2025-{pr_author}"
    if pr_title != expected:
        errors.append(
            f"!!  Неверный заголовок pull request.\n"
            f"    Ожидается: '{expected}'\n"
            f"    Получено:  '{pr_title}'\n"
        )
    else:
        print(f"....Заголовок PR корректный: {pr_title}")
    return errors


def validate_file_exists(pr_author):
    """Проверяет существование файла accepts_2025/<username>.yaml."""
    errors = []
    yaml_path = Path('accepts_2025') / f'{pr_author}.yaml'
    if not yaml_path.exists():
        errors.append(
            f"!!  Файл не найден.\n"
            f"    Ожидаемый путь: 'accepts_2025/{pr_author}.yaml'\n"
            f"    Убедитесь, что файл создан в правильной папке и имеет правильное имя."
        )
        return errors, None
    else:
        print(f"....Файл найден: {yaml_path.relative_to(Path.cwd())}")
        return errors, yaml_path


def validate_yaml_content(pr_author, yaml_path):
    errors = []
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if data is None:
            errors.append(f"!!  Файл '{yaml_path}' пустой или содержит только комментарии")
            return errors
        required_fields = ['github_username', 'first_name', 'last_name', 'repo', 'grading', 'agreement', 'agree_to_rules']
        for field in required_fields:
            if field not in data:
                errors.append(f"!!  В файле отсутствует обязательное поле: '{field}'")
        if 'github_username' in data:
            if not isinstance(data['github_username'], str) or not data['github_username'].strip():
                errors.append("!!  Поле 'github_username' должно быть непустой строкой")
            elif data['github_username'] != pr_author:
                errors.append(
                    f"!!  Несоответствие github_username.\n"
                    f"    Указано: '{data['github_username']}'\n"
                    f"    Ожидается: '{pr_author}' (ваш GitHub username)"
                )
            else:
                print(f"....github_username совпадает с логином автора PR: {pr_author}")
        if 'first_name' in data:
            if not isinstance(data['first_name'], str) or not data['first_name'].strip():
                errors.append("!!  Поле 'first_name' должно быть непустой строкой с именем")
            else:
                print(f"....Имя указано: {data['first_name']}")
        if 'last_name' in data:
            if not isinstance(data['last_name'], str) or not data['last_name'].strip():
                errors.append("!!  Поле 'last_name' должно быть непустой строкой с фамилией")
            else:
                print(f"....Фамилия указана: {data['last_name']}")
        if 'repo' in data:
            repo_val = data['repo']
            if repo_val == 'None':
                print(f"....Выбран формат сдачи: проект (repo=None)")
            elif isinstance(repo_val, str) and repo_val.strip().startswith(('http://', 'https://')):
                print(f"....Указан репозиторий для домашних заданий: {repo_val.strip()}")
            else:
                errors.append(
                    f"!!  Поле 'repo' должно быть строкой 'None' или валидным URL (начинающимся с http:// или https://).\n"
                    f"    Получено: '{repo_val}' (тип: {type(repo_val).__name__})"
                )
        if 'grading' in data:
            if data['grading'] not in ['homeworks', 'project']:
                errors.append(
                    f"!!  Поле 'grading' должно быть 'homeworks' или 'project'.\n"
                    f"    Получено: '{data['grading']}'"
                )
            else:
                print(f"....Формат сдачи: {data['grading']}")
        if 'agreement' in data:
            if not isinstance(data['agreement'], str) or not data['agreement'].strip():
                errors.append("!!  Поле 'agreement' должно содержать текст соглашения")
            else:
                if data['agreement'] != REFERENCE_AGREEMENT:
                    errors.append(
                        "!!  Текст соглашения не совпадает с официальным текстом курса.\n"
                        "    Скопируйте текст соглашения дословно из файла README.md в папке accepts_2025/"
                    )
                else:
                    print("....Текст соглашения совпадает с официальным текстом курса")
        if 'agree_to_rules' in data:
            if data['agree_to_rules'] != 'yes':
                errors.append(
                    f"!!  Поле 'agree_to_rules' должно содержать значение 'yes'.\n"
                    f"    Получено: '{data['agree_to_rules']}'"
                )
            else:
                print("....Согласие с правилами подтверждено (agree_to_rules: yes)")
    return errors


def validate_changed_files(pr_author, base_sha, head_sha):
    errors = []
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', base_sha, head_sha],
            capture_output=True,
            text=True,
            check=True,
            cwd='.'
        )
        changed_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
        accepts_changes = [f for f in changed_files if f.startswith('accepts_2025/')]
        if not accepts_changes:
            errors.append(
                "!!  Не обнаружено изменений в папке accepts_2025/\n"
                "    Убедитесь, что вы создали файл и сделали коммит."
            )
        elif len(accepts_changes) > 1:
            errors.append(
                f"!!  Обнаружено изменений в {len(accepts_changes)} файлах папки accepts_2025/:\n"
                f"    - {'\n   - '.join(accepts_changes)}\n"
                f"    Должен изменяться только один файл: {pr_author}.yaml"
            )
        else:
            changed = accepts_changes[0]
            expected = f'accepts_2025/{pr_author}.yaml'
            if changed != expected:
                errors.append(
                    f"!!  Изменён файл '{changed}', но ожидался '{expected}'\n"
                    f"    Имя файла должно совпадать с вашим GitHub username."
                )
            else:
                print(f"....Изменён только ожидаемый файл: {changed}")
    except subprocess.CalledProcessError as e:
        errors.append(f"!!  Не удалось проверить список изменённых файлов: {e}")
    return errors


def print_results(errors, warnings):
    print("=" * 70)
    if errors:
        print("ОБНАРУЖЕНЫ ОШИБКИ (требуют исправления):")
        print()
        for err in errors):
            print(err)
            print()
    else:
        print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print()
    print("=" * 70)


def main():
    env = load_env_vars()
    print_header(env['pr_author'])
    all_errors = []
    all_errors.extend(validate_branch_name(env['pr_author'], env['pr_branch']))
    print()
    all_errors.extend(validate_pr_title(env['pr_author'], env['pr_title']))
    print()
    file_errors, yaml_path = validate_file_exists(env['pr_author'])
    all_errors.extend(file_errors)
    print()
    if yaml_path:
        content_errors, content_warnings = validate_yaml_content(env['pr_author'], yaml_path)
        all_errors.extend(content_errors)
        all_warnings.extend(content_warnings)
        print()
    changed_errors, changed_warnings = validate_changed_files(
        env['pr_author'], env['base_sha'], env['head_sha']
    )
    all_errors.extend(changed_errors)
    all_warnings.extend(changed_warnings)
    print_results(all_errors, all_warnings)
    sys.exit(0 if not all_errors else 1)


if __name__ == '__main__':
    main()
