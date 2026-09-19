### 一、 整體題目架構與流程                                                                                                                                                   
                                                                                                                                                                                
  整個專案由 5 個核心檔案組成：                                                                                                                                                 
                                                                                                                                                                                
  1. main.py：FastAPI Web 服務，提供三個主要 API：                                                                                                                              
      • POST /login：傳入帳號、密碼、指定的 curve 與 hash，登入成功會產生 Token。                                                                                               
      • POST /refresh：驗證 Token，如果有效且更新次數 < 3，會更新 Token（每次呼叫會推進簽名中的 Nonce）。                                                                       
      • GET /telepathy：需要 Token 中的 payload["role"] == "medium"，成功後回傳 iv + telepathy.encrypt(flag, key, iv)。                                                         
  2. utils/__init__.py：                                                                                                                                                        
      • 管理 Token 的產生 (generate_token) 與驗證 (validate_token)。                                                                                                            
      • Token 格式為：session_uuid.header_b64.payload_b64.signature_b64。                                                                                                       
  3. utils/base64.py：自訂 Base64，字母表依 random.seed(b64seed) 打亂。                                                                                                         
  4. utils/dsa.py：自訂橢圓曲線數位簽名（ECDSA），但其簽名時的隨機數（Nonce k）使用了 LCG（線性同餘生成器） 更新。                                                              
  5. utils/telepathy.py：自訂的 32-byte 區塊密碼（類似簡化版 AES / SPN 結構）加 CBC 模式。                                                                                      
  ──────                                                                                                                                                                        
  ### 二、 核心漏洞與數學原理                                                                                                                                                   
                                                                                                                                                                                
  整個攻擊鏈可以清楚拆解為三個關卡：                                                                                                                                            
                                                                                                                                                                                
    [關卡 1: 自訂 Base64]                                                                                                                                                       
          ↓ 透過已知明文還原 Base64 字母表                                                                                                                                      
    [關卡 2: ECDSA LCG Nonce 漏洞]                                                                                                                                              
          ↓ 利用 /login 與 /refresh 收集連續簽名，解出私鑰 d                                                                                                                    
    [關卡 3: Token 偽造提權]                                                                                                                                                    
          ↓ 用私鑰 d 偽造 role="medium" 的 Token，打向 /telepathy                                                                                                               
    [關卡 4: 破解 telepathy 區塊加密]                                                                                                                                           
          ↓ 利用 Keyless 後置輪的特性，差分/爆破單字節還原 Key 或明文 Flag                                                                                                      
  ──────                                                                                                                                                                        
  #### 關卡 1：自訂 Base64 字母表還原                                                                                                                                           
                                                                                                                                                                                
  在 utils/base64.py 中：                                                                                                                                                       
                                                                                                                                                                                
    chars = list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/')                                                                                            
    self.base64_chars = ''.join(random.sample(chars, len(chars)))                                                                                                               
                                                                                                                                                                                
  • 特點：字母表只是標準 64 個字元的一種置換（Permutation）。                                                                                                                   
  • 已知明文攻擊（KPA）：                                                                                                                                                       
      • 我們在呼叫 /login 時，傳入了我們自選的 curve 和 hash。                                                                                                                  
      • 因此伺服器產生的 header 是完全已知的 JSON 字串：                                                                                                                        
      header_json = json.dumps({"curve": curve, "hash": hash}, separators=(",", ":"))                                                                                           
      • 同時 Token 的第二段就是 header_b64 = encoder.encode(header_json)。                                                                                                      
      • 標準 Base64 每 3 個 bytes 對應 4 個 Base64 字元。透過對比 header_json 與 header_b64，我們可以推算出大部分 Base64 索引對應的字元。                                       
      • 此外，由於是用 Python 的 random.seed(b64seed) 生成，只要拿到足夠的字元對應關係，甚至可以直接反推出 b64seed，還原出完整的字母表。                                        
                                                                                                                                                                                
  ──────                                                                                                                                                                        
  #### 關卡 2：ECDSA LCG 狀態洩漏（還原私鑰 d）                                                                                                                                 
                                                                                                                                                                                
  在 utils/dsa.py 中，檢視 sign 函數：                                                                                                                                          
                                                                                                                                                                                
    def sign(self, message: str) -> tuple[int, int]:                                                                                                                            
        m_hash = int.from_bytes(self.HASH(message).digest(), 'big')                                                                                                             
        self.k = (self.v * self.k + self.w) % self.n     # <--- 致命漏洞！                                                                                                      
        P = self.mul(self.k, self.G)                                                                                                                                            
        r = P[0] % self.n                                                                                                                                                       
        s = ((m_hash + r * self.d) * pow(self.k, -1, self.n)) % self.n                                                                                                          
        return r, s                                                                                                                                                             
                                                                                                                                                                                
  1. ECDSA 簽名方程：                                                                                                                                                           
                                                                                                                                                                                
    sᵢ ≡ kᵢ⁻¹(hᵢ + rᵢ · d) (mod n) ⟹ kᵢ ≡ sᵢ⁻¹hᵢ + sᵢ⁻¹rᵢ · d (mod n)                                                                                                           
                                                                                                                                                                                
  令 Aᵢ = sᵢ⁻¹hᵢ (mod n), Bᵢ = sᵢ⁻¹rᵢ (mod n)，則：                                                                                                                             
                                                                                                                                                                                
    kᵢ ≡ Aᵢ + Bᵢ · d (mod n)                                                                                                                                                    
                                                                                                                                                                                
  2. Nonce 之間的線性關係：                                                                                                                                                     
  每次產生簽名時，k 都會經過 LCG 轉換：                                                                                                                                         
                                                                                                                                                                                
    kᵢ₊₁ ≡ v · kᵢ + w (mod n)                                                                                                                                                   
                                                                                                                                                                                
  3. 解方程式求私鑰 d：                                                                                                                                                         
      • 我們可以先透過 /login 拿第 1 個簽名 (r₁, s₁)。                                                                                                                          
      • 透過 /refresh 呼叫 1 ~ 3 次（注意每個 session 最多 refresh 3 次），每次都會沿用同一個 session 的 d, v, w，但 k 會推進，因此我們可以得到 (r₂, s₂), (r₃, s₃), (r₄, s₄)。  
  情況 A：如果 v, w 為已知參數：                                                                                                                                                
  只需 2 組簽名即可解出一元一次方程式：                                                                                                                                         
                                                                                                                                                                                
    k₂ ≡ v · k₁ + w (mod n)                                                                                                                                                     
                                                                                                                                                                                
    A₂ + B₂ · d ≡ v(A₁ + B₁ · d) + w (mod n)                                                                                                                                    
                                                                                                                                                                                
    (B₂ - vB₁)d ≡ (vA₁ + w - A₂) (mod n)                                                                                                                                        
                                                                                                                                                                                
    d ≡ (B₂ - vB₁)⁻¹(vA₁ + w - A₂) (mod n)                                                                                                                                      
                                                                                                                                                                                
  情況 B：如果 v, w 為未知參數：                                                                                                                                                
  利用 4 組簽名消去 w 與 v：                                                                                                                                                    
                                                                                                                                                                                
  • k₂ - k₁, k₃ - k₂, k₄ - k₃ 形成等比數列，公比為 v。                                                                                                                          
  • (k₃ - k₂)² ≡ (k₄ - k₃)(k₂ - k₁) (mod n)。                                                                                                                                   
  • 將 kᵢ = Aᵢ + Bᵢ · d 帶入，展開後為關於私鑰 d 的二次多項式方程式，在有限域 𝔽ₙ 上求根即可直接解出私鑰 d！                                                                     
  ──────                                                                                                                                                                        
  #### 關卡 3：Token 偽造提權                                                                                                                                                   
                                                                                                                                                                                
  有了私鑰 d 以及 Base64 字母表之後：                                                                                                                                           
                                                                                                                                                                                
  1. 構造目標 Payload：                                                                                                                                                         
    {"account": "admin", "role": "medium", "timestamp": 1234567890}                                                                                                             
  （注意在 main.py 的 /telepathy 中，檢查的是 payload_dict["role"] != "medium"）。                                                                                              
  2. 使用自選的曲線與 Hash 產生 Header：                                                                                                                                        
    {"curve": "secp256k1", "hash": "sha256"}                                                                                                                                    
                                                                                                                                                                                
  3. 用求得的私鑰 d 對 f"{header_json}.{payload_json}" 進行標準 ECDSA 簽名（可自選一個隨機數 k 計算出 r, s）。                                                                  
  4. 將 Header、Payload、Signature 用先前還原的 Base64 編碼，組合成：                                                                                                           
  token = f"{session_uuid}.{header_b64}.{payload_b64}.{signature_b64}"                                                                                                          
  5. 帶上這個 Token 請求 GET /telepathy，即可通過校驗，獲得回傳的二進位密文（iv + ciphertext）。                                                                                
  ──────                                                                                                                                                                        
  #### 關卡 4：破解 telepathy 區塊密碼                                                                                                                                          
                                                                                                                                                                                
  檢視 utils/telepathy.py 中的 encrypt_block：                                                                                                                                  
                                                                                                                                                                                
    def encrypt_block(block: bytes, key: bytes, iv: bytes) -> tuple[bytes, bytes]:                                                                                              
        state = xor_bytes(block, iv)    # Step 1: S0 = P ^ IV                                                                                                                   
        state = sub_bytes(state)        # Step 2: S1 = SubBytes(S0)                                                                                                             
        state = xor_bytes(state, key)   # Step 3: S2 = S1 ^ Key                                                                                                                 
        state = sub_bytes(state)        # Step 4: S3 = SubBytes(S2)                                                                                                             
        state = shift_bytes(state)      # Step 5: S4 = ShiftBytes(S3)                                                                                                           
        state = sub_bytes(state)        # Step 6: S5 = SubBytes(S4)                                                                                                             
        state = shift_bytes(state)      # Step 7: C  = ShiftBytes(S5)                                                                                                           
        return state, state                                                                                                                                                     
                                                                                                                                                                                
  這是一個極度脆弱的結構：                                                                                                                                                      
                                                                                                                                                                                
  1. 密鑰加法（AddRoundKey）只執行了一次（Step 3）！                                                                                                                            
  2. Step 4、5、6、7 完全沒有使用 Key，全部是公開且可逆的置換與代換（SBOX 是標準 AES S-box，滿射可逆；SHIFT 也是可逆置換）。                                                    
  3. 這意味著：從 Ciphertext C 可以直接無密鑰反推回 Step 3 的輸出 S₂！                                                                                                          
                                                                                                                                                                                
    S₂ = SubBytes⁻¹(ShiftBytes⁻¹(SubBytes⁻¹(ShiftBytes⁻¹(C))))                                                                                                                  
                                                                                                                                                                                
  4. 現在看 S₂ 與明文、Key 的關係：                                                                                                                                             
                                                                                                                                                                                
    S₂ = SubBytes(P ⊕ IV) ⊕ Key                                                                                                                                                 
                                                                                                                                                                                
  如何求得 P 或 Key？                                                                                                                                                           
                                                                                                                                                                                
  • 方法 1（差分還原單字節）：                                                                                                                                                  
  因為我們已經能任意偽造 Token，我們可以請求 /telepathy 兩次（獲得兩組不同的隨機 IV 與密文）：                                                                                  
                                                                                                                                                                                
     (1)    (2)           ⎛      (1)⎞           ⎛      (2)⎞                                                                                                                     
    S    ⊕ S    = SubBytes⎝P ⊕ IV   ⎠ ⊕ SubBytes⎝P ⊕ IV   ⎠                                                                                                                     
     2      2                                                                                                                                                                   
  
  由於 Key 在 XOR 下被抵消了，對於第 1 個區塊的每一個 byte j ∈ [0, 31]：
  未知數只有 P[j]，取值範圍只有 0 ∼ 255！
  直接在 0 ∼ 255 內枚舉，256 次運算內就能唯一確定 P[j]。
  
  • 方法 2（已知前綴直接求 Key）：
  CTF 的 Flag 通常有固定格式（例如 flag{、CTF{ 等）。
  如果已知 P 的前幾位：
  
    Key = S₂ ⊕ SubBytes(P ⊕ IV)
  
  只要知道某個區塊的明文，就能直接反求出 Key！
  一旦有了 Key，整串密文的解密就變成了單純的逆向運算：
  
    P = SubBytes⁻¹(S₂ ⊕ Key) ⊕ IV
  
  直接解密所有後續區塊即可得到完整的 Flag。
  ──────
  ### 三、 解題腳本步驟總結
  
  1. 連線與收集簽名：
      • 呼叫 POST /login 拿到 Token 1。
      • 呼叫 1~3 次 POST /refresh 拿到 Token 2, 3, 4。
  2. 分析與計算：
      • 解出 Base64 置換表。
      • 利用連續簽名建立方程式，求出私鑰 d。
  3. 偽造與獲取密文：
      • 構造 role="medium" 的 Payload 並簽名。
      • 帶入 /telepathy 取得二進位密文。
  4. 解密密文：
      • 實作 inv_shift_bytes 與 inv_sub_bytes。
      • 從密文回推 S₂。
      • 利用已知明文前綴或兩次 IV 差分求出 Key，逆向解密取得 Plaintext Flag。
