<!-- omit in toc -->
# Contributing to Seq-Detective

First off, thanks for thinking about contributing!

Seq-Detective is currently pre-release code, and thus many areas,
including documentation and maintainer information, may be rough.

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



## I Have a Question
> If you want to ask a question, we assume that you have read the available [Documentation](https://github.com/czbiohub-sf/seq-tech-detective/tree/docs).

Before you ask a question, it is best to search for existing
[Issues](https://github.com/czbiohub-sf/seq-tech-detective/issues) that might help you. In case you
have found a suitable issue and still need clarification, you can write your question in this
issue. It is also advisable to search the internet for answers first. 

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](https://github.com/czbiohub-sf/seq-tech-detective/issues/new).
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (OS, CPU architecture), depending on what seems relevant.


More open-ended project discussions should occur in [internal slack].
> When this repository goes public, we may open GitHub Discussions as a project discussion space.

## I Want To Contribute

### Reporting Bugs

<!-- omit in toc -->
#### Before Submitting a Bug Report
TODO: describe how to access basic repro and logging information 


### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for Seq-Detective, **including
completely new features and minor improvements to existing functionality**. Following these
guidelines will help maintainers and the community to understand your suggestion and find related
suggestions. 

<!-- omit in toc -->
#### Before Submitting an Enhancement/Feature Request

- Make sure that you are using the latest version.
- Read the [documentation](https://github.com/czbiohub-sf/seq-tech-detective/tree/docs) carefully
  and find out if the functionality is already covered, maybe by an individual configuration.
- Perform a [search](https://github.com/czbiohub-sf/seq-tech-detective/issues) to see if the
  enhancement has already been suggested. If it has, add a comment to the existing issue instead of
  opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to make a
  strong case to convince the project's developers of the merits of this feature. Keep in mind that
  we want features that will be useful to the majority of our users and not just a small subset. If
  you're just targeting a minority of users, consider writing a third-party tool.

<!-- omit in toc -->
#### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://github.com/czbiohub-sf/seq-tech-detective/issues).

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as
  possible. 
- **Describe the current behavior** and **explain which behavior you expected to see instead** and
  why. At this point you can also tell which alternatives do not work for you. 
- **Give context for why this enhancement would be useful** to most Seq-Detective users. You may
  also want to point out the other projects that solved it better and which could serve as
  inspiration.
  
  
<!-- omit in toc -->
#### New Sequencing Library Suggestion

Seq-Detective aims to support a wide range of sequencing library technologies.  However, there will
always be new sequencing methods and variations.  If there's something you think we missed, submit
an [issue](https://github.com/czbiohub-sf/seq-tech-detective/issues)!

Make sure to follow the points below when requesting support for a new sequencing library.

- Gather as much information as possible about the technology beforehand.
 - Name
 - Original Publication
 - Other documentation, e.g. [scg lib structs entry](https://teichlab.github.io/scg_lib_structs/)
   or [seqspec](https://igvf.github.io/seqspec/) or original research.
 - Other information that may be helpful to implementation: barcode onlists, strand bias, error
   rate, prevalence of use, canonical processing tools, even relation to other technologies can
   be useful!
- **Provide links to (ideally multiple, inter-species) example FASTQ in the wild (usually SRA runs)**
- For more obscure technology, justifying a particular use case may help with prioritization (for
  example, some sequencing techniques are prominent in a specific species despite being otherwise
  unpopular)

Please note that at this time, Seq-Detective only considers the following categories of sequencing
technnology to be in scope:
- **bulk RNA-Seq** available as FASTA or FASTQ
- **single-cell RNA-seq** available as FASTA or FASTQ

### Your First Code Contribution

Unsure where to begin contributing to Seq-Detective? You can start by looking through these `beginner` and `help-wanted` issues:

* [Beginner issues][beginner] - issues which should only require a few lines of code, and a test or two.
* [Help wanted issues][help-wanted] - issues which should be a bit more involved than `beginner` issues.

<!-- omit in toc -->
#### Local development

TODO: git development loop
briefly:

- clone the repository
- create a branch
- make changes (remember to add tests, if adding a new feature or changing behavior)
- run `make fmt` and `make lint`.  fix and repeat until no warnings are triggered by your code.
- commit your changes, trying to follow the [commit message guidelines](#commit-guidelines)
- push your changes
- open a pull request

### Pull Requests

Please follow these steps to have your contribution considered by the maintainers:

1. Follow the [styleguides](#styleguides)

While the prerequisites above must be satisfied prior to having your pull request reviewed, the
reviewer(s) may ask you to complete additional design work, tests, or other changes before your
pull request can be ultimately accepted.

<!-- omit in toc -->
#### Merging

Pull requests (PRs) are either squashed or rebased onto upstream:
 - Internal PRs are usually rebased
 - PRs with discussion are usually squashed
 - PRs with many (> 4) commits for a single task are usually squashed

## Style Guides

### Git Commit Messages

We (loosely) follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)

- Limit the first line to 80 characters or less
- Start the commit message with an appropriate change type:
 - `feat:` for feature additions
 - `fix:` for bug behavior fixes
 - `perf:` for performance optimization
 - `chore:` for code hygiene, cleanup, refactoring work
 - `test:` for test additions
 - `docs:` for documentation improvements
- A scope may be provided to a commit’s type, to provide additional contextual information and is
  contained within parenthesis, e.g., `feat(fingerprints): add inDrop variant used by lab A`
- For a single commit with multiple change categories, first line is for the highest rank.  then,
  enumerate other changes in the commit body, following conventional commit format.
- Reference issues and pull requests liberally after the first line
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")


Use `git rebase -i` to correct mistakes before merging.

### C Style Guide
 - **Indent with tabs**
 - **Tab width is 4**
 - **Indent size is 4**
 - **Align with spaces**
 - **Brace style is K&R**
   - briefly, this means open brace goes on the same line of constructs except function definition.
 - **Alignment**: contiguous assigments are currently aligned for readability.  this can have obvious
   detrimental effects in some cases, especially when automated by `clang-format`.  leave a blank
   or comment line between assignments that should not be aligned.
 - **Pointer declarations**: keep pointer with the variable name, e.g. `int *p, *p2`.

For more thorough style guidelines, see for now `.clang-format`
feel free to open an issue if something doesn't seem right.

clang-format runs with `make fmt`.  use it to reduce churn.
some code is not handled well by clang-format, such as struct array initialization.
for these, block out manually-formatted code with `// clang-format off|on` like so:

```
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
TODO: more examples

 - we currently do not use [Annex K](https://open-std.org/jtc1/sc22/wg14/www/docs/n1967.htm) safe
   versions of deprecated buffer handling functions
   because in our use the Annex K interface is redundant with our own checks and bug-prone. 
   Therefore, these functions (for example strcpy) are not flagged by `clang-tidy`.
   use appropriate caution when employing deprecated buffer handling functions.

 - we disable `clang-diagnostic-missing-field-initializers` because it flags fingerprints with
   implied 0 sentinel entries.

TODO: other notable linter warnings we disable?


### Shell Script Style Guide
use [shellcheck](https://github.com/koalaman/shellcheck) to lint bash scripts.
this also runs when `make lint`

### asm style guide

### 