# sonic-host-services Issue Decisions

## #134: sshd: Too many authentication failures [OPEN]
**判定: DOC → docs/system/ssh-authentication-failures.md**
SSH 接続時に複数の秘密鍵を試行した結果 MaxAuthTries に引っかかるエラー。`-o PubkeyAuthentication=no` で回避可能。SONiC 固有ではなく OpenSSH の一般挙動だが、SONiC デバイスへの接続でよく遭遇する問題として有用。
