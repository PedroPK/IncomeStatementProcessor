# Contribuindo para Income Statement Processor

Obrigado por ter interesse em contribuir! Este documento fornece orientações para participar do desenvolvimento.

## 🤝 Código de Conduta

Todas as contribuições devem seguir os princípios de:
- Respeito e inclusão
- Qualidade de código
- Documentação clara
- Testes adequados

## 🚀 Como Começar

### 1. Prepare o Ambiente

```bash
# Clone o repositório (seu fork)
git clone https://github.com/seu-usuario/income-statement-processor.git
cd income-statement-processor

# Crie um branch para sua feature
git checkout -b feature/sua-feature

# Instale dependências de desenvolvimento
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest black pylint  # ferramentas adicionais
```

### 2. Desenvolvimento

#### Estrutura de Código

```python
# Sempre use type hints
from dataclasses import dataclass
from typing import list

def process_entry(entry: Entry) -> float:
    """Processa uma entrada e retorna o total."""
    return entry.valor_2024 + entry.valor_2025
```

#### Convenções

- **Nomes**: `snake_case` para funções/variáveis, `PascalCase` para classes
- **Docstrings**: Use docstrings em português para funções públicas
- **Imports**: Agrupe em: stdlib → third-party → local (separado por linhas em branco)
- **Linha máxima**: 100 caracteres (preferência PEP 8)
- **Encoding**: UTF-8 em todos os arquivos

#### Exemplo de Função Bem Estruturada

```python
def parse_novo_banco(filename: str, pages_text: list[str],
                     pages_tables: list[list]) -> list[Entry]:
    """
    Extrai entradas do Novo Banco.
    
    Args:
        filename: Nome do arquivo PDF
        pages_text: Lista de textos por página
        pages_tables: Lista de tabelas extraídas
        
    Returns:
        Lista de entradas estruturadas
        
    Raises:
        ValueError: Se estrutura do PDF não for reconhecida
    """
    entries: list[Entry] = []
    full_text = '\n'.join(pages_text)
    
    # Seu código aqui
    
    return entries
```

### 3. Adicionando um Novo Parser (exemplo: Novo Banco)

#### Passo 1: Criar o parser em `src/parser.py`

```python
def parse_novo_banco(filename: str, pages_text: list[str],
                     pages_tables: list[list]) -> list[Entry]:
    entries: list[Entry] = []
    inst = 'Novo Banco LLC'
    cnpj = 'XX.XXX.XXX/XXXX-XX'
    ano = extract_year('\n'.join(pages_text))
    
    # Implementação específica
    
    return entries
```

#### Passo 2: Registrar em `detect_institution()`

```python
def detect_institution(filename: str, first_page: str) -> str:
    # ... código existente ...
    if 'novo*banco' in fn_lower:
        return 'novo_banco'
    # ...
```

#### Passo 3: Adicionar ao dispatcher em `parse_file()`

```python
def parse_file(filepath: str) -> list[Entry]:
    # ... código existente ...
    if institution == 'novo_banco':
        return parse_novo_banco(filename, pages_text, pages_tables)
    # ...
```

#### Passo 4: Testes

```python
# test_novo_banco.py
def test_parse_novo_banco_sample():
    from src.parser import parse_novo_banco
    
    # Use um PDF de amostra real
    entries = parse_novo_banco('sample_novo_banco.pdf', [...], [...])
    
    assert len(entries) > 0, "Deveria extrair pelo menos 1 entrada"
    assert entries[0].instituicao == 'Novo Banco LLC'
    assert entries[0].valor_2025 > 0
```

### 4. Testes

#### Rodando Testes

```bash
# Teste um arquivo específico
python3 -m pytest test/test_parser.py -v

# Teste com cobertura
python3 -m pytest --cov=src test/

# Teste rápido de parser específico
python3 -c "from src.parser import parse_novo_banco; print(parse_novo_banco(...))"
```

#### Padrão de Testes

- Prefixo `test_` para todos os testes
- Use `assert` para validações simples
- Use `pytest.raises()` para exceções
- Cobertura mínima: 80%

### 5. Formatação de Código

```bash
# Formate com black
black src/

# Verifique com pylint
pylint src/

# Type checking com mypy (optional)
mypy src/
```

### 6. Git Workflow

#### Commits

```bash
# Commits atômicos com mensagens claras
git commit -m "parser: add Novo Banco institution support

- Implement parse_novo_banco() for structured table extraction
- Handle account balance parsing from page 1
- Support renda fixa and stocks in grupo 04, 03
- Tests: 12 entries extracted from sample PDF"
```

#### Formato de Mensagem

```
tipo: descrição breve

Descrição detalhada (opcional):
- Ponto 1
- Ponto 2

Fixes #123
```

**Tipos comuns:**
- `feat`: Nova funcionalidade
- `fix`: Bug fix
- `docs`: Documentação
- `refactor`: Refatoração
- `test`: Testes
- `perf`: Performance

#### Pull Request

1. Push seu branch: `git push origin feature/sua-feature`
2. Abra um PR no GitHub com descrição clara
3. Aguarde review
4. Faça ajustes se solicitado
5. Merge após aprovação

### 7. Adicionando Dependências

```bash
# Instale
pip install novo-pacote

# Atualize requirements.txt
pip freeze > requirements.txt

# Commit
git add requirements.txt
git commit -m "deps: add novo-pacote==X.Y.Z for [motivo]"
```

### 8. Documentação

#### Atualize README.md se:
- Nova instituição adicionada
- Nova funcionalidade principal
- Mudança em como usar

#### Atualize CHANGELOG.md:
- Sempre que faz merge de uma feature/fix
- Use formato [Keep a Changelog](https://keepachangelog.com/)

#### Exemplo CHANGELOG entry:

```markdown
### Adicionado
- Suporte para Novo Banco com 15 entradas de ativos

### Corrigido
- Avenue parser agora extrai corretamente valores com IRRF
```

## 🐛 Reportando Bugs

### Checklist

- [ ] Reproduz em v1.0.0?
- [ ] Checou issues abertas (não é duplicate)?
- [ ] Coletou logs completos?
- [ ] Usou PDF de exemplo?

### Template

```markdown
## Descrição
Breve descrição do bug

## Passos para Reproduzir
1. Coloque arquivo X em `input/`
2. Execute `python3 -m src.main`
3. Abra XLSX gerado

## Comportamento Esperado
X entradas extraídas

## Comportamento Atual
Y entradas (ou 0)

## Logs
[Cole output completo]

## Ambiente
- OS: macOS 14.5
- Python: 3.11.2
- pdfplumber: 0.11.9
```

## 💡 Sugestões de Melhoria

Antes de sugerir:
1. Verifique se já não foi proposto em Issues
2. Descreva o problema que resolve
3. Dê exemplos de uso

## 📚 Recursos Úteis

- [pdfplumber docs](https://github.com/jamesturk/pdfplumber)
- [openpyxl docs](https://openpyxl.readthedocs.io/)
- [gspread docs](https://docs.gspread.org/)
- [PEP 8](https://pep8.org/) - Guia de estilo Python
- [Real Python - Type Hints](https://realpython.com/python-type-checking/)

## ❓ Dúvidas?

Abra uma discussion ou issue com a tag `question`.

---

Obrigado por contribuir! 🎉
