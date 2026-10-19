#!/usr/bin/env bash

SIGNING_CERT_NAME="Zombie Fire Daily Local Code Signing"
SIGNING_STATE_DIR="${HOME:?}/Library/Application Support/向僵尸开炮日常助手/signing"
SIGNING_FINGERPRINT_FILE="$SIGNING_STATE_DIR/identity.sha1"

signing_keychain() {
  local keychain
  for keychain in "$HOME/Library/Keychains/login.keychain-db" "$HOME/Library/Keychains/login.keychain"; do
    if [[ -f "$keychain" ]]; then
      printf '%s\n' "$keychain"
      return 0
    fi
  done
  echo "找不到当前用户的登录钥匙串；请在钥匙串访问中确认 $HOME/Library/Keychains/login.keychain-db 存在。" >&2
  return 1
}

named_signing_identities() {
  local keychain="$1"
  /usr/bin/security find-identity -v -p codesigning "$keychain" 2>/dev/null |
    awk -v name="\"$SIGNING_CERT_NAME\"" 'index($0, name) { print tolower($2) }'
}

export_named_certificates() {
  local keychain="$1" directory="$2"
  /usr/bin/security find-certificate -a -c "$SIGNING_CERT_NAME" -p "$keychain" > "$directory/named-certificates.pem" 2>/dev/null || return 1
  awk -v directory="$directory" '
    /-----BEGIN CERTIFICATE-----/ { number++; file = sprintf("%s/certificate-%d.pem", directory, number) }
    file { print > file }
    /-----END CERTIFICATE-----/ { close(file); file = "" }
  ' "$directory/named-certificates.pem"
}

certificate_fingerprint() {
  /usr/bin/openssl x509 -in "$1" -noout -fingerprint -sha1 2>/dev/null |
    sed 's/.*=//; s/://g' | tr '[:upper:]' '[:lower:]'
}

trust_certificate_for_codesigning() {
  local keychain="$1" certificate="$2"
  # 仅在当前用户钥匙串授予代码签名用途信任，不改系统信任或其他用途。
  /usr/bin/security add-trusted-cert -p codeSign -k "$keychain" "$certificate" >/dev/null
}

require_signing_identity() {
  local keychain expected identities identity_count actual
  keychain="$(signing_keychain)" || return 1

  if [[ ! -f "$SIGNING_FINGERPRINT_FILE" ]]; then
    echo "尚未设置稳定的本地签名身份；请先运行：npm run setup:signing" >&2
    return 1
  fi
  expected="$(tr -d '[:space:]' < "$SIGNING_FINGERPRINT_FILE" | tr '[:upper:]' '[:lower:]')"
  if [[ ! "$expected" =~ ^[0-9a-f]{40}$ ]]; then
    echo "签名身份指纹配置损坏：$SIGNING_FINGERPRINT_FILE；为避免更换身份，请先检查该文件。" >&2
    return 1
  fi

  identities="$(named_signing_identities "$keychain")"
  identity_count="$(printf '%s\n' "$identities" | sed '/^$/d' | wc -l | tr -d '[:space:]')"
  if [[ "$identity_count" != "1" ]]; then
    echo "登录钥匙串中应有且只有一个有效的“$SIGNING_CERT_NAME”代码签名身份；当前找到 $identity_count 个。未更换身份。" >&2
    return 1
  fi
  actual="$(printf '%s\n' "$identities" | sed -n '1p')"
  if [[ "$actual" != "$expected" ]]; then
    echo "登录钥匙串中的签名证书与已保存指纹不一致；为避免静默更换身份，已停止。" >&2
    return 1
  fi
  printf '%s\n' "$actual"
}

designated_requirement() {
  local path="$1" output requirement
  output="$(/usr/bin/codesign --display -r- "$path" 2>&1)" || {
    echo "无法读取签名的 designated requirement：$path" >&2
    return 1
  }
  requirement="$(printf '%s\n' "$output" | sed -n 's/^designated => //p' | sed -n '1p')"
  if [[ -z "$requirement" ]]; then
    echo "签名没有可读取的 designated requirement：$path" >&2
    return 1
  fi
  if [[ "$requirement" == *cdhash* ]]; then
    echo "拒绝仅绑定 cdhash 的 designated requirement：$path" >&2
    return 1
  fi
  printf '%s\n' "$requirement"
}
