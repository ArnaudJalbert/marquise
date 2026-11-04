# Naming guidance in *Clean Code*

Research date: 2026-11-04. This note captures context for defining Marquise naming rules. It is not proposed policy text.

## Editions and attribution

The 2008 edition has a chapter titled “Meaningful Names” as Chapter 2. O’Reilly credits that chapter to Tim Ottinger, while listing Robert C. Martin as the book’s author. The chapter outline covers intention-revealing names, disinformation, meaningful distinctions, pronounceability, searchability, encodings, mental mapping, class and method names, consistent terminology, domain vocabulary, and context. [O’Reilly, *Clean Code*, Chapter 2](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml)

The 2025 second edition has a revised “Meaningful Names” chapter as Chapter 4, credited to Tim Ottinger and Robert C. Martin. Martin’s introduction describes it as an evolution of Ottinger’s earlier naming rules. The publisher preview still shows the chapter’s focus on intention-revealing names. [O’Reilly, *Clean Code*, 2nd edition, Chapter 4](https://www.oreilly.com/library/view/clean-code-a/9780135398586/ch04.xhtml)

## Useful context

The chapter frames naming as communication across variables, functions, arguments, classes, packages, and other code elements, not merely a casing convention. Its visible introduction says names should reveal intent and that the care spent choosing them pays back for readers. [O’Reilly, *Clean Code*, Chapter 2](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml)

The chapter outline gives several distinct concerns that can inform a repo rule: names should distinguish concepts accurately, avoid misleading cues and needless decoding, remain usable in conversation and search, and carry enough context to make their meaning clear. These are a synthesis of the publisher’s listed section headings, not a claim that the preview exposes the chapter’s full arguments. [O’Reilly, *Clean Code*, Chapter 2](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml)

For Marquise, this separates two questions: a language or linter can prescribe spelling and casing, while a naming rule can ask whether the identifier tells the reader what the value means or what role it plays. This distinction is an application of the chapter’s outline to the repo’s existing Ruff and Oxlint setup, not wording from the book.

## Limits

The publisher pages expose the table of contents and opening passages, but not the complete chapter text. This note uses the chapter outline as a reliable map of topics and avoids treating every heading as a fully verified detailed rule. The second edition’s presentation differs from the 2008 edition, so a future rule that cites the book should name which edition it follows. [O’Reilly, *Clean Code*, Chapter 2](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml), [O’Reilly, *Clean Code*, 2nd edition, Chapter 4](https://www.oreilly.com/library/view/clean-code-a/9780135398586/ch04.xhtml)

## Sources

- [O’Reilly, *Clean Code: A Handbook of Agile Software Craftsmanship*, Chapter 2](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml)
- [O’Reilly, *Clean Code: A Handbook of Agile Software Craftsmanship*, 2nd edition, Chapter 4](https://www.oreilly.com/library/view/clean-code-a/9780135398586/ch04.xhtml)
