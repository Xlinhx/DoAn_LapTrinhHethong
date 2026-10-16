# ==============================================================================
# Makefile - Đề tài 17: Implement ls with -a, -l, -R, -S (VKU System Programming)
# Chuẩn biên dịch: C11 + POSIX.1-2008 / XSI (_XOPEN_SOURCE=700)
# ==============================================================================

CC       := gcc
CFLAGS   := -Wall -Wextra -Werror -pedantic -std=c11 \
            -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700 \
            -Iinclude -O2 -g
SAN_FLAGS:= -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS  :=

TARGET       := myls
SAN_TARGET   := myls_sanitize
BUILD_DIR    := build
SRC_DIR      := src
INC_DIR      := include

SRCS     := $(SRC_DIR)/main.c \
            $(SRC_DIR)/options.c \
            $(SRC_DIR)/directory.c \
            $(SRC_DIR)/sorting.c \
            $(SRC_DIR)/display.c

OBJS     := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(SRCS))
DIST_NAME:= vku-system-programming-ls

.PHONY: all clean test sanitize demo log dist help

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(SAN_TARGET): $(SRCS) $(INC_DIR)/myls.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(SAN_FLAGS) -o $@ $(SRCS) $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c $(INC_DIR)/myls.h | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: $(TARGET)
	@bash tests/run_tests.sh ./$(TARGET)

sanitize: $(SAN_TARGET)
	@ASAN_OPTIONS="verify_asan_link_order=0:detect_leaks=1:halt_on_error=1" \
	 UBSAN_OPTIONS="print_stacktrace=1:halt_on_error=1" \
	 MYLS_TEST_SANITIZE=1 \
	 bash tests/run_tests.sh ./$(SAN_TARGET)

demo: $(TARGET)
	@bash tests/run_demo.sh

log:
	git log --stat --decorate > LOG

dist: all
	rm -f tests/test_internals tests/fault_inject.so
	tar --exclude='__pycache__' --exclude='*.pyc' --exclude='docs/assets/raw_illustrations' \
		-czf $(DIST_NAME).tar.gz \
		$(SRC_DIR) $(INC_DIR) tests docs evidence scripts \
		Makefile README.md CHECKLIST.md LOG .gitignore .gitattributes requirements-docs.txt
	tar --exclude='__pycache__' --exclude='*.pyc' --exclude='docs/assets/raw_illustrations' \
		-cf $(DIST_NAME).tar \
		$(SRC_DIR) $(INC_DIR) tests docs evidence scripts \
		Makefile README.md CHECKLIST.md LOG .gitignore .gitattributes requirements-docs.txt
	@echo "[OK] Created submission packages: $(DIST_NAME).tar.gz and $(DIST_NAME).tar"

clean:
	rm -rf $(BUILD_DIR) $(TARGET) $(SAN_TARGET) tests/test_internals tests/fault_inject.so $(DIST_NAME).tar $(DIST_NAME).tar.gz

help:
	@echo "Available targets:"
	@echo "  make          - Compile $(TARGET) executable"
	@echo "  make test     - Run automated test suite against GNU ls in /tmp"
	@echo "  make sanitize - Compile with ASan/UBSan/LSan and run full test suite"
	@echo "  make demo     - Run demonstration scenario on isolated Linux fixture"
	@echo "  make log      - Export git commit history to LOG file"
	@echo "  make dist     - Build submission archives (.tar and .tar.gz)"
	@echo "  make clean    - Remove compiled objects and binaries"
