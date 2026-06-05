<!-- omit in toc -->
# Contributing to Seq-Detective

Thanks for thinking about contributing!

<!-- omit in toc -->
## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [I Want To Contribute](#i-want-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Your First Code Contribution](#your-first-code-contribution)
- [Pull Requests](#pull-requests)
- [Style Guides](#style-guides)
- [Git-Commit Messages](#git-commit-messages)
- [C Style Guide](#c-style-guide)
- [Shell script style guide](#shell-script-style-guide)

## Code of Conduct

We expect contributors to interact professionally and in good faith.  Open an issue or contact the
maintainers if you encounter conduct you believe is inappropriate.

## I Have a Question

Before asking a question, search the existing
[Issues](https://github.com/czbiohub-sf/seq-tech-detective/issues) — your question may already be
answered.  If not:

- Open an [Issue](https://github.com/czbiohub-sf/seq-tech-detective/issues/new).
- Provide as much context as you can about what you're running into.
- Include platform and version information (OS, CPU architecture, tool versions) as relevant.

Open-ended project discussions are welcome in
[GitHub Discussions](https://github.com/czbiohub-sf/seq-tech-detective/discussions).

## I Want To Contribute

### Reporting Bugs

Before submitting a bug report, reproduce the issue with a minimal example if possible.  When
opening the issue, include:

- The command you ran and the full output (stdout and stderr).
- Your OS, CPU architecture, and the version of each relevant tool (hisat2, featureCounts, fastp,
  Python, polars).
- A FASTQ sample or SRA accession that reproduces the problem, if you are able to share one.

### Suggesting Enhancements

Enhancement suggestions are tracked as [GitHub issues](https://github.com/czbiohub-sf/seq-tech-detective/issues).

Before submitting:

- Confirm you are on the latest version.
- Search for existing issues covering the same suggestion.
- Consider whether the enhancement fits the scope of the project (see below).

When submitting:

- Use a clear and descriptive title.
- Describe the current behavior and what you expect instead.
- Give context for why the change would be useful to other users.

#### New Sequencing Library Support — Out of Scope in Core Mode

Full technology classification (identifying specific sequencing chemistries) is not available in
this release.  New sequencing library fingerprint requests are therefore out of scope for Core Mode
and will not be acted on at this time.

When broader technology classification is released, the following will be relevant for library
requests:

- Name and original publication.
- Other documentation, e.g. a [scg lib structs entry](https://teichlab.github.io/scg_lib_structs/)
  or [seqspec](https://igvf.github.io/seqspec/) spec.
- Barcode onlists, strand bias, canonical processing tools, and relation to similar technologies.
- Links to example FASTQ files in the wild (SRA runs preferred; multiple accessions and species
  are helpful).
- Justification for prioritization if the technology is niche.

Seq-Detective considers the following categories of sequencing technology to be in scope:

- **bulk RNA-seq** available as FASTQ
- **single-cell RNA-seq** available as FASTQ

### Your First Code Contribution

- Clone the repository and create a branch off `main`.
- Make changes; add tests if you are adding a feature or changing behavior.
- Run `make fmt` and `make lint`; fix all warnings before committing.
- Follow the [commit message guidelines](#git-commit-messages).
- Push your branch and open a pull request.

```bash
git clone git@github.com:czbiohub-sf/seq-tech-detective.git
cd seq-tech-detective
git switch main && git pull
git checkout -b <branch-name>
# make and test changes
make fmt
make lint
git push origin <branch-name>
# then open a pull request
```

### Pull Requests

Follow the style guides before requesting review.  Reviewers may ask for additional changes,
tests, or design work before a PR is accepted.

#### Merging

- Internal PRs are usually rebased.
- PRs with discussion are usually squashed.
- PRs with more than four commits for a single task are usually squashed.

## Style Guides

### Git Commit Messages

We (loosely) follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/).

- Limit the first line to 80 characters.
- Start with a change type: `feat:`, `fix:`, `perf:`, `chore:`, `test:`, `docs:`.
- A scope may follow the type in parentheses: `feat(judge): add DeTCT heuristic`.
- For commits with multiple change categories, the first line covers the highest-rank type;
  enumerate others in the body.
- Reference issues and pull requests after the first line.
- Use present tense and imperative mood: "Add feature", not "Added feature" or "Adds feature".

Use `git rebase -i` to clean up commits before merging.

### C Style Guide

- **Indent with tabs; tab width and indent size are 4.**
- **Brace style is K&R** — open brace on the same line as the construct, except for function
  definitions.
- **Alignment**: contiguous assignments may be aligned for readability.  Insert a blank or comment
  line between assignment blocks that should not be aligned together.
- **Pointer declarations**: pointer with the variable name — `int *p, *p2`.

See `.clang-format` for complete rules.  Run `make fmt` before committing to reduce style churn.

Some constructs (e.g. struct array initializers) are not handled well by clang-format; bracket
these with `// clang-format off` / `// clang-format on`:

```c
// clang-format off
static struct sd_library_fingerprint fingerprints[] = {
    {
        "10x-RNA-v2", {
            { SD_R1, SD_FWD,  SD_ONLIST, { 0,  0}, {16, 16}, {"cb_10x_737K-august-2016.txt"} },
            { SD_I1, SD_FWD,  SD_ONLIST, { 0,  0}, { 8,  8}, {"index7_onlist.txt"} },
            { SD_NONE },
        }
    },
};
// clang-format on
```

We do not use [Annex K](https://open-std.org/jtc1/sc22/wg14/www/docs/n1967.htm) safe variants of
deprecated buffer-handling functions; in our use the interface is redundant with our own checks and
error-prone.  Use appropriate caution with deprecated buffer-handling functions regardless.

`clang-diagnostic-missing-field-initializers` is suppressed because it fires on fingerprint
entries with implied zero sentinel fields.

### Shell Script Style Guide

Use [shellcheck](https://github.com/koalaman/shellcheck) to lint shell scripts.  This also runs
with `make lint`.
