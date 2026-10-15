# ==============================================================================
# Makefile - Đề tài 17: Implement ls with -a, -l, -R, -S (VKU System Programming)
# Chuẩn biên dịch: C11 + POSIX.1-2008 / XSI (_XOPEN_SOURCE=700)
# ==============================================================================

CC       := gcc
CFLAGS   := -Wall -Wextra -Werror -pedantic -std=c11 \
            -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700 \
            -Iinclude -O2 -g
LDFLAGS  :=

TARGET   := myls
BUILD_DIR:= build
SRC_DIR  := src
INC_DIR  := include

SRCS     := $(SRC_DIR)/main.c \
            $(SRC_DIR)/options.c \
            $(SRC_DIR)/directory.c \
            $(SRC_DIR)/sorting.c \
            $(SRC_DIR)/display.c

OBJS     := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRCS))
DIST_NAME:= vku-system-programming-ls

.PHONY: all clean test demo log dist help

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c $(INC_DIR)/myls.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: $(TARGET)
	@bash tests/run_tests.sh

demo: $(TARGET)
	@bash tests/run_demo.sh

log:
	git log --stat --decorate > LOG

dist: all log
	tar -czf $(DIST_NAME).tar.gz \
		$(SRC_DIR) $(INC_DIR) tests docs evidence \
		Makefile README.md CHECKLIST.md LOG .gitignore
	tar -cf $(DIST_NAME).tar \
		$(SRC_DIR) $(INC_DIR) tests docs evidence \
		Makefile README.md CHECKLIST.md LOG .gitignore
	@echo "[OK] Created submission packages: $(DIST_NAME).tar.gz and $(DIST_NAME).tar"

clean:
	rm -rf $(BUILD_DIR) $(TARGET) $(DIST_NAME).tar $(DIST_NAME).tar.gz

help:
	@echo "Available targets:"
	@echo "  make          - Compile $(TARGET) executable"
	@echo "  make test     - Run automated test suite against GNU ls in /tmp"
	@echo "  make demo     - Run standard demonstration commands and save evidence"
	@echo "  make log      - Export git commit history to LOG file"
	@echo "  make dist     - Build submission archives (.tar and .tar.gz)"
	@echo "  make clean    - Remove compiled objects and binaries"
