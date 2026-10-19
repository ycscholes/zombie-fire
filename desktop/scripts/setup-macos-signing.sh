#!/usr/bin/env bash
set -euo pipefail

DESKTOP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$DESKTOP_ROOT/scripts/macos-signing-common.sh"

# 为本机创建或恢复稳定签名身份；--check 只读校验，供构建提前失败。
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "稳定本地签名身份只能在 macOS 登录钥匙串中设置。" >&2
  exit 2
fi
if [[ "${1:-}" == "--check" ]]; then
  require_signing_identity >/dev/null
  echo "稳定本地签名身份可用。"
  exit 0
elif [[ -n "${1:-}" ]]; then
  echo "用法：$0 [--check]" >&2
  exit 2
fi
for tool in /usr/bin/security /usr/bin/codesign /usr/bin/openssl; do
  if [[ ! -x "$tool" ]]; then
    echo "缺少 macOS 签名工具：$tool" >&2
    exit 2
  fi
done

KEYCHAIN="$(signing_keychain)"
mkdir -p "$SIGNING_STATE_DIR"
chmod 700 "$SIGNING_STATE_DIR"
umask 077
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zombie-fire-signing.XXXXXX")"
STATE_TEMP=""
cleanup() {
  [[ -z "$STATE_TEMP" ]] || rm -f "$STATE_TEMP"
  [[ -z "$TEMP_DIR" ]] || rm -rf "$TEMP_DIR"
}
trap cleanup EXIT
chmod 700 "$TEMP_DIR"

save_fingerprint() {
  local fingerprint="$1"
  STATE_TEMP="$SIGNING_STATE_DIR/.identity.sha1.$$"
  printf '%s\n' "$fingerprint" > "$STATE_TEMP"
  chmod 600 "$STATE_TEMP"
  mv "$STATE_TEMP" "$SIGNING_FINGERPRINT_FILE"
  STATE_TEMP=""
}

certificate_for_fingerprint() {
  local expected="$1" certificate fingerprint match=""
  if ! export_named_certificates "$KEYCHAIN" "$TEMP_DIR"; then
    return 1
  fi
  for certificate in "$TEMP_DIR"/certificate-*.pem; do
    [[ -f "$certificate" ]] || continue
    fingerprint="$(certificate_fingerprint "$certificate")"
    if [[ "$fingerprint" == "$expected" ]]; then
      if [[ -n "$match" ]]; then
        echo "登录钥匙串中出现重复证书；为避免误信任，已停止。" >&2
        return 2
      fi
      match="$certificate"
    fi
  done
  [[ -n "$match" ]] || return 1
  printf '%s\n' "$match"
}

recover_or_create_identity() {
  local identities identity_count fingerprint certificate cert_count
  if [[ -f "$SIGNING_FINGERPRINT_FILE" ]]; then
    fingerprint="$(tr -d '[:space:]' < "$SIGNING_FINGERPRINT_FILE" | tr '[:upper:]' '[:lower:]')"
    if [[ ! "$fingerprint" =~ ^[0-9a-f]{40}$ ]]; then
      echo "签名身份指纹配置损坏：$SIGNING_FINGERPRINT_FILE；为避免更换身份，请先检查该文件。" >&2
      return 1
    fi
    if require_signing_identity >/dev/null 2>&1; then
      echo "复用已配置的稳定本地签名身份。"
      return 0
    fi
    certificate="$(certificate_for_fingerprint "$fingerprint")" || {
      echo "已保存的签名证书不在登录钥匙串中；为避免轮换身份，未生成新证书。" >&2
      return 1
    }
    if ! trust_certificate_for_codesigning "$KEYCHAIN" "$certificate"; then
      echo "无法恢复该证书的用户级 codeSign 信任；请完成 macOS 信任提示后重试。未更换身份。" >&2
      return 1
    fi
    if ! require_signing_identity >/dev/null; then
      echo "恢复 codeSign 信任后仍无法使用已保存的签名身份；请检查钥匙串私钥和授权提示。" >&2
      return 1
    fi
    echo "已恢复原签名证书的用户级 codeSign 信任，并复用原身份。"
    return 0
  fi

  identities="$(named_signing_identities "$KEYCHAIN")"
  identity_count="$(printf '%s\n' "$identities" | sed '/^$/d' | wc -l | tr -d '[:space:]')"
  if [[ "$identity_count" == "1" ]]; then
    fingerprint="$(printf '%s\n' "$identities" | sed -n '1p')"
    save_fingerprint "$fingerprint"
    echo "复用登录钥匙串中唯一的同名有效代码签名身份。"
    return 0
  elif [[ "$identity_count" != "0" ]]; then
    echo "登录钥匙串中存在多个同名有效身份；为避免选错证书或轮换身份，未作修改。" >&2
    return 1
  fi

  if export_named_certificates "$KEYCHAIN" "$TEMP_DIR"; then
    cert_count="$(find "$TEMP_DIR" -name 'certificate-*.pem' -type f | wc -l | tr -d '[:space:]')"
  else
    cert_count=0
  fi
  if [[ "$cert_count" == "1" ]]; then
    certificate="$TEMP_DIR/certificate-1.pem"
    fingerprint="$(certificate_fingerprint "$certificate")"
    if [[ ! "$fingerprint" =~ ^[0-9a-f]{40}$ ]]; then
      echo "无法读取登录钥匙串中现有证书的指纹；为避免轮换身份，未作修改。" >&2
      return 1
    fi
    if ! trust_certificate_for_codesigning "$KEYCHAIN" "$certificate"; then
      echo "无法恢复现有证书的用户级 codeSign 信任；请完成 macOS 信任提示后重试。未生成新证书。" >&2
      return 1
    fi
    identities="$(named_signing_identities "$KEYCHAIN")"
    if [[ "$(printf '%s\n' "$identities" | sed '/^$/d' | wc -l | tr -d '[:space:]')" == "1" ]] \
      && [[ "$(printf '%s\n' "$identities" | sed -n '1p')" == "$fingerprint" ]]; then
      save_fingerprint "$fingerprint"
      echo "恢复了钥匙串中同名证书的用户级 codeSign 信任，并保存该原身份。"
      return 0
    fi
    echo "钥匙串中已有同名证书，但没有唯一有效的配对私钥；为避免轮换身份，未生成新证书。" >&2
    return 1
  elif [[ "$cert_count" != "0" ]]; then
    echo "登录钥匙串中存在多个同名证书；为避免信任错误证书或轮换身份，未作修改。" >&2
    return 1
  fi

  # 仅在本地临时目录生成密钥；以一次 PKCS#12 导入，避免留下半成品钥匙串条目。
  PRIVATE_KEY="$TEMP_DIR/private-key.pem"
  CERTIFICATE="$TEMP_DIR/certificate.pem"
  IDENTITY_BUNDLE="$TEMP_DIR/identity.p12"
  /usr/bin/openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 \
    -keyout "$PRIVATE_KEY" -out "$CERTIFICATE" \
    -subj "/CN=$SIGNING_CERT_NAME" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature" \
    -addext "extendedKeyUsage=codeSigning" >/dev/null 2>&1 || {
      echo "无法生成本地代码签名证书；检查 OpenSSL 安装后重试。" >&2
      return 1
    }
  fingerprint="$(certificate_fingerprint "$CERTIFICATE")"
  if [[ ! "$fingerprint" =~ ^[0-9a-f]{40}$ ]]; then
    echo "无法读取新证书指纹；没有保存签名身份配置。" >&2
    return 1
  fi
  P12_PASSWORD="$(/usr/bin/openssl rand -hex 32)" || {
    echo "无法生成临时导入口令；没有导入或保存签名身份。" >&2
    return 1
  }
  if [[ ! "$P12_PASSWORD" =~ ^[0-9a-f]{64}$ ]] \
    || ! /usr/bin/openssl pkcs12 -export -inkey "$PRIVATE_KEY" -in "$CERTIFICATE" \
      -out "$IDENTITY_BUNDLE" -passout "pass:$P12_PASSWORD" >/dev/null 2>&1; then
    unset P12_PASSWORD
    echo "无法打包临时签名身份；没有导入或保存签名身份。" >&2
    return 1
  fi
  if ! /usr/bin/security import "$IDENTITY_BUNDLE" -f pkcs12 -t agg -P "$P12_PASSWORD" \
    -x -k "$KEYCHAIN" -T /usr/bin/codesign >/dev/null 2>&1; then
    unset P12_PASSWORD
    echo "无法将签名身份安全导入登录钥匙串；请解锁钥匙串并完成 macOS 显示的授权提示后重试。没有放宽私钥访问范围。" >&2
    return 1
  fi
  unset P12_PASSWORD
  if ! trust_certificate_for_codesigning "$KEYCHAIN" "$CERTIFICATE"; then
    echo "证书和私钥已导入，但用户级 codeSign 信任未能设置；请完成 macOS 信任提示后再次运行 setup。不会生成新身份。" >&2
    return 1
  fi
  identities="$(named_signing_identities "$KEYCHAIN")"
  identity_count="$(printf '%s\n' "$identities" | sed '/^$/d' | wc -l | tr -d '[:space:]')"
  if [[ "$identity_count" != "1" || "$(printf '%s\n' "$identities" | sed -n '1p')" != "$fingerprint" ]]; then
    echo "钥匙串没有返回刚导入的唯一有效代码签名身份；请检查证书、私钥和信任设置。" >&2
    return 1
  fi
  save_fingerprint "$fingerprint"
  echo "稳定本地签名身份已就绪。仅供本机使用，不是 Developer ID 或公证证书。"
}

recover_or_create_identity
