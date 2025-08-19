#!/bin/bash
#
# Homebrew Cask Update Script
# Modularized from Makefile for better maintainability
#

set -euo pipefail

# Color definitions
readonly BLUE='\033[0;34m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly RED='\033[0;31m'
readonly RESET='\033[0m'

# Configuration
readonly APP_NAME="hf-model-downloader"
readonly HOMEBREW_TAP_REPO="homebrew-tap"
readonly CASK_FILE="Casks/hf-model-downloader.rb"
readonly WORK_DIR="tmp"

# Global variables
VERSION=""
BRANCH_NAME=""
ARM64_SHA256=""
X86_64_SHA256=""

log_info() {
    echo -e "${BLUE}$1${RESET}"
}

log_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

log_warning() {
    echo -e "${YELLOW}$1${RESET}"
}

log_error() {
    echo -e "${RED}❌ $1${RESET}" >&2
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "${WORK_DIR}"
}

trap cleanup EXIT

validate_environment() {
    if [[ -z "${GH_PAT:-}" ]]; then
        log_error "GH_PAT environment variable is required"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "git command not found"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl command not found"
        exit 1
    fi
    
    if ! command -v shasum &> /dev/null; then
        log_error "shasum command not found"
        exit 1
    fi
}

get_version() {
    # Priority: use environment variable VERSION if available (for CI/CD)
    if [[ -n "${VERSION:-}" ]]; then
        log_info "Using version from environment: $VERSION"
    elif [[ -f "pyproject.toml" ]]; then
        VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
        log_info "Version extracted from pyproject.toml: $VERSION"
    else
        log_error "Version not found in environment or pyproject.toml"
        exit 1
    fi
    
    if [[ -z "$VERSION" ]]; then
        log_error "Could not determine version"
        exit 1
    fi
    
    BRANCH_NAME="update-hf-model-downloader-${VERSION}"
    log_info "Final version: $VERSION"
}

prepare_workspace() {
    log_info "Preparing workspace..."
    rm -rf "${WORK_DIR}"
    mkdir -p "${WORK_DIR}"
}

download_release_files() {
    log_info "Downloading DMG files..."
    local base_url="https://github.com/samzong/hf-model-downloader/releases/download/v${VERSION}"
    local max_retries=10
    local retry_delay=30
    
    # Function to check if file exists and download it
    download_with_retry() {
        local url="$1"
        local output="$2"
        local retries=0
        
        while [ $retries -lt $max_retries ]; do
            log_info "Attempting to download $(basename "$url") (attempt $((retries + 1))/$max_retries)..."
            
            if curl -f -L -o "$output" "$url"; then
                log_success "Successfully downloaded $(basename "$url")"
                return 0
            else
                log_warning "Download failed, retrying in ${retry_delay} seconds..."
                sleep $retry_delay
                retries=$((retries + 1))
            fi
        done
        
        log_error "Failed to download $(basename "$url") after $max_retries attempts"
        return 1
    }
    
    download_with_retry "${base_url}/${APP_NAME}-arm64.dmg" "${WORK_DIR}/${APP_NAME}-arm64.dmg"
    download_with_retry "${base_url}/${APP_NAME}-x86_64.dmg" "${WORK_DIR}/${APP_NAME}-x86_64.dmg"
}

calculate_checksums() {
    log_info "Calculating SHA256 checksums..."
    ARM64_SHA256=$(shasum -a 256 "${WORK_DIR}/${APP_NAME}-arm64.dmg" | cut -d ' ' -f 1)
    X86_64_SHA256=$(shasum -a 256 "${WORK_DIR}/${APP_NAME}-x86_64.dmg" | cut -d ' ' -f 1)
    
    log_info "ARM64 SHA256: $ARM64_SHA256"
    log_info "x86_64 SHA256: $X86_64_SHA256"
}

clone_tap_repository() {
    log_info "Cloning Homebrew tap repository..."
    cd "${WORK_DIR}"
    git clone "https://${GH_PAT}@github.com/samzong/${HOMEBREW_TAP_REPO}.git"
    cd "${HOMEBREW_TAP_REPO}"
    
    # Ensure remote URL uses token for subsequent push operations
    git remote set-url origin "https://${GH_PAT}@github.com/samzong/${HOMEBREW_TAP_REPO}.git"
    
    git checkout -b "${BRANCH_NAME}"
}

update_cask_file() {
    log_info "Updating cask file..."
    
    if [[ ! -f "$CASK_FILE" ]]; then
        log_error "Cask file not found: $CASK_FILE"
        exit 1
    fi
    
    log_info "Current cask file content:"
    cat "$CASK_FILE"
    
    # Update version (using more robust approach)
    local temp_file="${CASK_FILE}.tmp"
    sed "s/version \".*\"/version \"${VERSION}\"/g" "$CASK_FILE" > "$temp_file"
    mv "$temp_file" "$CASK_FILE"
    
    # Update SHA256 values using a more readable approach
    if grep -q "on_arm" "$CASK_FILE"; then
        log_info "Updating SHA256 values for on_arm/on_intel format..."
        
        # Create a temporary awk script for better maintainability
        cat > update_sha.awk << 'EOF'
/on_arm/,/end/ { 
    if (/sha256/) {
        gsub(/"[^"]*"/, "\"" arm_sha "\"")
    }
}
/on_intel/,/end/ { 
    if (/sha256/) {
        gsub(/"[^"]*"/, "\"" intel_sha "\"")
    }
}
{ print }
EOF
        
        awk -v arm_sha="$ARM64_SHA256" -v intel_sha="$X86_64_SHA256" -f update_sha.awk "$CASK_FILE" > "${CASK_FILE}.tmp"
        mv "${CASK_FILE}.tmp" "$CASK_FILE"
        rm -f update_sha.awk
        
        log_success "SHA256 values updated"
    else
        log_error "on_arm/on_intel format not found in cask file"
        exit 1
    fi
    
    log_info "Updated cask file content:"
    cat "$CASK_FILE"
}

commit_and_push_changes() {
    log_info "Checking for changes..."
    
    if ! git diff --quiet "$CASK_FILE"; then
        log_info "Changes detected, committing and pushing..."
        
        git add "$CASK_FILE"
        git config user.name "GitHub Actions"
        git config user.email "actions@github.com"
        git commit -m "chore: update hf-model-downloader to v${VERSION}"
        git push -u origin "$BRANCH_NAME"
        
        log_success "Changes committed and pushed"
    else
        log_error "No changes detected in cask file"
        exit 1
    fi
}

create_pull_request() {
    log_info "Creating pull request..."
    
    local pr_body="Auto-generated PR

- Version: ${VERSION}
- ARM64 SHA256: ${ARM64_SHA256}
- x86_64 SHA256: ${X86_64_SHA256}"
    
    local pr_data
    pr_data=$(cat << EOF
{
  "title": "chore: update hf-model-downloader to v${VERSION}",
  "body": $(echo "$pr_body" | jq -R -s .),
  "head": "$BRANCH_NAME",
  "base": "main"
}
EOF
)
    
    log_info "Creating PR with data: $pr_data"
    
    curl -X POST \
        -H "Authorization: token ${GH_PAT}" \
        -H "Content-Type: application/json" \
        "https://api.github.com/repos/samzong/${HOMEBREW_TAP_REPO}/pulls" \
        -d "$pr_data"
    
    log_success "Pull request created successfully"
}

main() {
    log_info "Starting Homebrew cask update process..."
    
    validate_environment
    get_version
    prepare_workspace
    download_release_files
    calculate_checksums
    clone_tap_repository
    update_cask_file
    commit_and_push_changes
    create_pull_request
    
    log_success "Homebrew cask update process completed"
}

# Only run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi