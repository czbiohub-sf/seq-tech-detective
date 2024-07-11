prefix=/usr/local
exec_prefix=$(prefix)
bindir=$(exec_prefix)/bin

NAME=seq-detective
SRC=./src
BIN=./bin
CC=gcc
CLANG_TIDY=clang-tidy-16
CFLAGS=-g -O3 -Wextra -Wall -Wconversion -Wpedantic -std=gnu2x -mtune=native -fopenmp -lc
DEBUG_CFLAGS=$(CFLAGS) -DDEBUG -g2 -gsplit-dwarf -fno-omit-frame-pointer
CLANG_CFLAGS=$(CFLAGS)
LINT_FLAGS=src/*.[ch] --checks="-clang-diagnostic-gnu*" --header-filter=".*"
OBJS=main.o

SHELL:=/bin/bash
DATAPROMPT:=data source directory to link: 

# bold teal
T_HL:=[36;1m
# reset
T_0:=[m

.PHONY: $(NAME) debug data readme lint lint_c lint_py lint_sh

$(NAME): $(BIN)/$(NAME)

debug: $(BIN)/$(NAME)_debug

$(SRC)/%.o: $(SRC)/%.c $(SRC)/%.h
	$(CC) $(CFLAGS) -c $< -o $@

$(BIN)/$(NAME): $(SRC)/*.o
	mkdir -p $(BIN)
	$(CC) $(CFLAGS) -o$@ $^

$(BIN)/$(NAME)_debug: $(SRC)/*.o
	mkdir -p $(BIN)
	$(CC) $(DEBUG_CFLAGS) -o$@ $^

clean:
	rm -f $(SRC)/*.o
	rm -rf $(BIN)/$(NAME)


data:
#	@:don't echo, readline completion  bold teal prompt,                 initial path  store to
	@read         -e                   -p '$(T_HL)$(DATAPROMPT)$(T_0)' -i `pwd`        DATASRC; \
	ln -s "$$DATASRC" data

readme:
	./scripts/util/update_readme_tree.sh

lint_c:
	-$(CLANG_TIDY) $(LINT_FLAGS) -- -isystem /usr/lib/clang/16.0.6/include/ $(CLANG_CFLAGS)

lint_py:
	-ruff check

lint_sh:
	-shellcheck --extended-analysis=true -o all -e SC2312 -S style classify-rnaseq

lint: lint_py lint_sh lint_c
