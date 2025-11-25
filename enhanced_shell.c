#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <errno.h>
#include <signal.h>
#include <fcntl.h>
#include <time.h>
#include <pwd.h>
#include <glob.h>

#define MAX_LINE 1024
#define MAX_ARGS 64
#define MAX_HISTORY 100
#define MAX_ALIASES 50
#define MAX_JOBS 10

// Color codes for output
#define COLOR_RESET   "\x1b[0m"
#define COLOR_RED     "\x1b[31m"
#define COLOR_GREEN   "\x1b[32m"
#define COLOR_YELLOW  "\x1b[33m"
#define COLOR_BLUE    "\x1b[34m"
#define COLOR_MAGENTA "\x1b[35m"
#define COLOR_CYAN    "\x1b[36m"
#define COLOR_WHITE   "\x1b[37m"

// Structure for command history
typedef struct {
    char commands[MAX_HISTORY][MAX_LINE];
    int count;
    int current;
} history_t;

// Structure for aliases
typedef struct {
    char name[64];
    char value[256];
} alias_t;

// Structure for background jobs
typedef struct {
    pid_t pid;
    char command[MAX_LINE];
    int job_id;
    int active;
} job_t;

// Global variables
history_t history = {0};
alias_t aliases[MAX_ALIASES];
int alias_count = 0;
job_t jobs[MAX_JOBS];
int job_count = 0;
int last_exit_status = 0;
char current_dir[MAX_LINE];
char home_dir[MAX_LINE];

// Function prototypes
void execute_command(char **args);
void execute_pipeline(char **args);
void execute_background(char **args);
char **parse_input(char *line);
void handle_builtin(char **args);
int is_builtin(char *cmd);
void add_to_history(char *command);
void print_history(void);
void change_directory(char *path);
void set_alias(char *name, char *value);
void print_aliases(void);
void expand_aliases(char **args);
void expand_variables(char **args);
void handle_redirection(char **args);
void print_jobs(void);
void cleanup_jobs(void);
void handle_signals(void);
void print_prompt(void);
void initialize_shell(void);
int has_wildcards(char *str);
char **expand_wildcards(char **args);

// Signal handlers
void sigchld_handler(int sig) {
    int status;
    pid_t pid;
    
    while ((pid = waitpid(-1, &status, WNOHANG)) > 0) {
        // Find and mark job as completed
        for (int i = 0; i < job_count; i++) {
            if (jobs[i].pid == pid && jobs[i].active) {
                jobs[i].active = 0;
                printf("\n[%d] Done\t\t%s\n", jobs[i].job_id, jobs[i].command);
                fflush(stdout);
                break;
            }
        }
    }
}

void sigint_handler(int sig) {
    printf("\n");
    print_prompt();
    fflush(stdout);
}

// Initialize shell environment
void initialize_shell(void) {
    // Set up signal handlers
    signal(SIGCHLD, sigchld_handler);
    signal(SIGINT, sigint_handler);
    
    // Get home directory
    struct passwd *pw = getpwuid(getuid());
    if (pw) {
        strcpy(home_dir, pw->pw_dir);
    } else {
        strcpy(home_dir, "/");
    }
    
    // Get current directory
    if (getcwd(current_dir, sizeof(current_dir)) == NULL) {
        strcpy(current_dir, home_dir);
    }
    
    // Initialize some default aliases
    set_alias("ll", "ls -la");
    set_alias("la", "ls -la");
    set_alias("l", "ls -l");
    set_alias("...", "cd ../..");
    set_alias("grep", "grep --color=auto");
}

// Enhanced prompt with colors and git branch
void print_prompt(void) {
    char *user = getenv("USER");
    char hostname[256];
    gethostname(hostname, sizeof(hostname));
    
    // Check if we're in a git repository
    char git_branch[64] = "";
    FILE *fp = popen("git branch 2>/dev/null | grep '^*' | cut -d' ' -f2", "r");
    if (fp) {
        if (fgets(git_branch, sizeof(git_branch), fp)) {
            git_branch[strcspn(git_branch, "\n")] = 0; // Remove newline
        }
        pclose(fp);
    }
    
    // Print colorized prompt
    printf("%s%s@%s%s:%s%s%s", 
           COLOR_GREEN, user ? user : "user", hostname, COLOR_RESET,
           COLOR_BLUE, current_dir, COLOR_RESET);
    
    if (strlen(git_branch) > 0) {
        printf("%s(%s)%s", COLOR_YELLOW, git_branch, COLOR_RESET);
    }
    
    printf("%s$ %s", last_exit_status == 0 ? COLOR_GREEN : COLOR_RED, COLOR_RESET);
    fflush(stdout);
}

// Check if string contains wildcards
int has_wildcards(char *str) {
    return strchr(str, '*') != NULL || strchr(str, '?') != NULL || strchr(str, '[') != NULL;
}

// Expand wildcards using glob
char **expand_wildcards(char **args) {
    static char *expanded[MAX_ARGS];
    int expanded_count = 0;
    
    for (int i = 0; args[i] != NULL && expanded_count < MAX_ARGS - 1; i++) {
        if (has_wildcards(args[i])) {
            glob_t glob_result;
            if (glob(args[i], GLOB_TILDE, NULL, &glob_result) == 0) {
                for (size_t j = 0; j < glob_result.gl_pathc && expanded_count < MAX_ARGS - 1; j++) {
                    expanded[expanded_count++] = strdup(glob_result.gl_pathv[j]);
                }
                globfree(&glob_result);
            } else {
                expanded[expanded_count++] = strdup(args[i]);
            }
        } else {
            expanded[expanded_count++] = strdup(args[i]);
        }
    }
    expanded[expanded_count] = NULL;
    return expanded;
}

// Expand environment variables
void expand_variables(char **args) {
    for (int i = 0; args[i] != NULL; i++) {
        if (args[i][0] == '$') {
            char *var_name = args[i] + 1;
            char *value = getenv(var_name);
            if (value) {
                free(args[i]);
                args[i] = strdup(value);
            }
        }
        // Handle ~ expansion
        else if (args[i][0] == '~') {
            char expanded_path[MAX_LINE];
            if (args[i][1] == '/' || args[i][1] == '\0') {
                snprintf(expanded_path, sizeof(expanded_path), "%s%s", home_dir, args[i] + 1);
                free(args[i]);
                args[i] = strdup(expanded_path);
            }
        }
    }
}

// Add command to history
void add_to_history(char *command) {
    if (history.count < MAX_HISTORY) {
        strcpy(history.commands[history.count], command);
        history.count++;
    } else {
        // Shift history and add new command
        for (int i = 0; i < MAX_HISTORY - 1; i++) {
            strcpy(history.commands[i], history.commands[i + 1]);
        }
        strcpy(history.commands[MAX_HISTORY - 1], command);
    }
    history.current = history.count;
}

// Print command history
void print_history(void) {
    printf("%sCommand History:%s\n", COLOR_CYAN, COLOR_RESET);
    for (int i = 0; i < history.count; i++) {
        printf("%3d  %s\n", i + 1, history.commands[i]);
    }
}

// Set alias
void set_alias(char *name, char *value) {
    // Check if alias already exists
    for (int i = 0; i < alias_count; i++) {
        if (strcmp(aliases[i].name, name) == 0) {
            strcpy(aliases[i].value, value);
            return;
        }
    }
    
    // Add new alias
    if (alias_count < MAX_ALIASES) {
        strcpy(aliases[alias_count].name, name);
        strcpy(aliases[alias_count].value, value);
        alias_count++;
    }
}

// Print all aliases
void print_aliases(void) {
    printf("%sAliases:%s\n", COLOR_CYAN, COLOR_RESET);
    for (int i = 0; i < alias_count; i++) {
        printf("alias %s='%s'\n", aliases[i].name, aliases[i].value);
    }
}

// Expand aliases in command
void expand_aliases(char **args) {
    if (args[0] == NULL) return;
    
    for (int i = 0; i < alias_count; i++) {
        if (strcmp(args[0], aliases[i].name) == 0) {
            // Parse alias value
            char *alias_copy = strdup(aliases[i].value);
            char **alias_args = parse_input(alias_copy);
            
            // Shift original args and prepend alias args
            int alias_argc = 0;
            while (alias_args[alias_argc] != NULL) alias_argc++;
            
            int orig_argc = 0;
            while (args[orig_argc] != NULL) orig_argc++;
            
            // Create new args array
            static char *new_args[MAX_ARGS];
            int new_argc = 0;
            
            // Copy alias args
            for (int j = 0; j < alias_argc && new_argc < MAX_ARGS - 1; j++) {
                new_args[new_argc++] = strdup(alias_args[j]);
            }
            
            // Copy original args (skip first one)
            for (int j = 1; j < orig_argc && new_argc < MAX_ARGS - 1; j++) {
                new_args[new_argc++] = strdup(args[j]);
            }
            new_args[new_argc] = NULL;
            
            // Copy back to original args
            for (int j = 0; j < new_argc; j++) {
                if (args[j]) free(args[j]);
                args[j] = new_args[j];
            }
            for (int j = new_argc; j < MAX_ARGS; j++) {
                args[j] = NULL;
            }
            
            free(alias_copy);
            free(alias_args);
            break;
        }
    }
}

// Change directory with enhanced features
void change_directory(char *path) {
    char old_dir[MAX_LINE];
    strcpy(old_dir, current_dir);
    
    if (path == NULL || strcmp(path, "~") == 0) {
        path = home_dir;
    } else if (strcmp(path, "-") == 0) {
        path = getenv("OLDPWD");
        if (path == NULL) {
            printf("mysh: cd: OLDPWD not set\n");
            return;
        }
    }
    
    if (chdir(path) == 0) {
        setenv("OLDPWD", old_dir, 1);
        if (getcwd(current_dir, sizeof(current_dir)) == NULL) {
            strcpy(current_dir, path);
        }
        setenv("PWD", current_dir, 1);
    } else {
        perror("mysh: cd");
        last_exit_status = 1;
    }
}

// Print background jobs
void print_jobs(void) {
    printf("%sBackground Jobs:%s\n", COLOR_CYAN, COLOR_RESET);
    for (int i = 0; i < job_count; i++) {
        if (jobs[i].active) {
            printf("[%d] Running\t\t%s\n", jobs[i].job_id, jobs[i].command);
        }
    }
}

// Clean up finished jobs
void cleanup_jobs(void) {
    for (int i = 0; i < job_count; i++) {
        if (!jobs[i].active) {
            // Remove job from array
            for (int j = i; j < job_count - 1; j++) {
                jobs[j] = jobs[j + 1];
            }
            job_count--;
            i--;
        }
    }
}

// Check if command is a built-in
int is_builtin(char *cmd) {
    char *builtins[] = {"cd", "pwd", "exit", "history", "alias", "unalias", "jobs", "help", "export", "unset", "echo", NULL};
    for (int i = 0; builtins[i] != NULL; i++) {
        if (strcmp(cmd, builtins[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

// Handle built-in commands
void handle_builtin(char **args) {
    if (strcmp(args[0], "cd") == 0) {
        change_directory(args[1]);
    } else if (strcmp(args[0], "pwd") == 0) {
        printf("%s\n", current_dir);
    } else if (strcmp(args[0], "exit") == 0) {
        int exit_code = args[1] ? atoi(args[1]) : last_exit_status;
        printf("Goodbye!\n");
        exit(exit_code);
    } else if (strcmp(args[0], "history") == 0) {
        print_history();
    } else if (strcmp(args[0], "alias") == 0) {
        if (args[1] == NULL) {
            print_aliases();
        } else {
            char *equals = strchr(args[1], '=');
            if (equals) {
                *equals = '\0';
                set_alias(args[1], equals + 1);
            }
        }
    } else if (strcmp(args[0], "jobs") == 0) {
        print_jobs();
    } else if (strcmp(args[0], "help") == 0) {
        printf("%sMysh - Advanced Shell%s\n", COLOR_CYAN, COLOR_RESET);
        printf("Built-in commands:\n");
        printf("  cd [dir]     - Change directory\n");
        printf("  pwd          - Print working directory\n");
        printf("  exit [code]  - Exit shell\n");
        printf("  history      - Show command history\n");
        printf("  alias [name=value] - Set or show aliases\n");
        printf("  jobs         - Show background jobs\n");
        printf("  help         - Show this help\n");
        printf("  export VAR=value - Set environment variable\n");
        printf("  echo [text]  - Print text\n");
    } else if (strcmp(args[0], "export") == 0) {
        if (args[1]) {
            char *equals = strchr(args[1], '=');
            if (equals) {
                *equals = '\0';
                setenv(args[1], equals + 1, 1);
            }
        }
    } else if (strcmp(args[0], "echo") == 0) {
        for (int i = 1; args[i] != NULL; i++) {
            printf("%s", args[i]);
            if (args[i + 1] != NULL) printf(" ");
        }
        printf("\n");
    }
    last_exit_status = 0;
}

// Execute command with background support
void execute_background(char **args) {
    pid_t pid = fork();
    if (pid == 0) {
        // Child process
        signal(SIGINT, SIG_DFL);
        execvp(args[0], args);
        perror("mysh");
        exit(EXIT_FAILURE);
    } else if (pid > 0) {
        // Parent process - add to jobs list
        if (job_count < MAX_JOBS) {
            jobs[job_count].pid = pid;
            jobs[job_count].job_id = job_count + 1;
            jobs[job_count].active = 1;
            
            // Build command string
            char cmd_str[MAX_LINE] = "";
            for (int i = 0; args[i] != NULL; i++) {
                strcat(cmd_str, args[i]);
                if (args[i + 1] != NULL) strcat(cmd_str, " ");
            }
            strcpy(jobs[job_count].command, cmd_str);
            
            printf("[%d] %d\n", jobs[job_count].job_id, pid);
            job_count++;
        }
    } else {
        perror("mysh: fork");
        last_exit_status = 1;
    }
}

// Execute regular command
void execute_command(char **args) {
    pid_t pid = fork();
    if (pid == 0) {
        // Child process
        signal(SIGINT, SIG_DFL);
        execvp(args[0], args);
        perror("mysh");
        exit(EXIT_FAILURE);
    } else if (pid > 0) {
        // Parent process
        int status;
        waitpid(pid, &status, 0);
        last_exit_status = WEXITSTATUS(status);
    } else {
        perror("mysh: fork");
        last_exit_status = 1;
    }
}

// Parse input line into arguments
char **parse_input(char *line) {
    static char *args[MAX_ARGS];
    int argc = 0;
    char *token = strtok(line, " \t\n");
    
    while (token != NULL && argc < MAX_ARGS - 1) {
        args[argc++] = strdup(token);
        token = strtok(NULL, " \t\n");
    }
    args[argc] = NULL;
    return args;
}

// Main shell loop
int main() {
    char line[MAX_LINE];
    char **args;
    
    initialize_shell();
    
    printf("%sWelcome to MyShell - Advanced Terminal%s\n", COLOR_CYAN, COLOR_RESET);
    printf("Type 'help' for available commands\n\n");
    
    while (1) {
        cleanup_jobs();
        print_prompt();
        
        if (!fgets(line, MAX_LINE, stdin)) {
            printf("\n");
            break;
        }
        
        // Remove trailing newline
        line[strcspn(line, "\n")] = 0;
        
        // Skip empty lines
        if (strlen(line) == 0) {
            continue;
        }
        
        // Add to history
        add_to_history(line);
        
        // Check for background execution
        int background = 0;
        int len = strlen(line);
        if (len > 0 && line[len - 1] == '&') {
            background = 1;
            line[len - 1] = '\0';
        }
        
        // Parse command
        args = parse_input(line);
        if (args[0] == NULL) {
            continue;
        }
        
        // Expand aliases
        expand_aliases(args);
        
        // Expand variables
        expand_variables(args);
        
        // Expand wildcards
        args = expand_wildcards(args);
        
        // Handle built-in commands
        if (is_builtin(args[0])) {
            handle_builtin(args);
        } else {
            // Execute external command
            if (background) {
                execute_background(args);
            } else {
                execute_command(args);
            }
        }
        
        // Clean up dynamically allocated memory
        for (int i = 0; args[i] != NULL; i++) {
            free(args[i]);
        }
        
        printf("__PROMPT__\n");
        fflush(stdout);
    }
    
    return 0;
}
