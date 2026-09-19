### 突破口 1：JSON 解析器差異與身分驗證繞過 (Parser Differential)                                       
                                                                                                          
  • 相關檔案：checkout.go:12-31 與 session.py:40-46                                                       
  • 漏洞成因：                                                                                            
      • Go Gateway 使用 github.com/buger/jsonparser，當遇到 JSON 物件中存在重複的 Key 時，checkout.go:13  
      會優先讀取 第一個 出現的 Key。                                                                      
      • Python 後端在 app.py:26 使用標準庫的 json.loads()，其標準字典行為是 後者覆蓋前者（Last-Key        
      Wins）。                                                                                            
  • 突破點：                                                                                              
  在 /api/checkout 接口中，Go Gateway 的 checkout.go:12 要求 x == "u" 且未檢查 Key 是否重複；而 Python 的 
  session.py:43 則是當 x == "a" 時會簽發管理員的 Bearer Token。                                           
  因此，透過傳入包含重複 Key 的 JSON（第一個 x 設為 "u"，第二個 x 設為 "a"），Go 會檢驗通過，而 Python    
  則會簽發 Bearer Token。                                                                                 
  ──────                                                                                                  
  ### 突破口 2：證明生成與 Attestation Token (Scope B)                                                    
                                                                                                          
  • 相關檔案：state.py:483-614、model.py:201-214 與 logic.py:128-184                                      
  • 漏洞成因：                                                                                            
  後續後台報表接口（如 /api/admin/report）需要帶有 scope: "b" 的認證憑證（X-Token-B）。                   
  • 突破點：                                                                                              
      • 題目設計了一套 Z3 幾何與故障域驗證邏輯（Attestation）。                                           
      • 透過調用 /api/attestation/challenge 獲取當前 case 參數，利用 z3-solver 計算滿足 model.py:201      
      的最小策略與遮罩證明。                                                                              
      • 提交證明給 /api/attestation/submit 取得 X-Token-A 與審計快照（Snapshot                            
      Receipts），再比對世界模型發送 /api/attestation/complete，即可取得具備完整查詢參數的 X-Token-B。    
                                                                                                          
  ──────                                                                                                  
  ### 突破口 3：IEEE 754 雙精度浮點數精度截斷碰撞                                                         
                                                                                                          
  • 相關檔案：windows.go:10-25 與 documents.py:32-45                                                      
  • 漏洞成因：                                                                                            
  在 documents.py:32 中，若要將查詢通道切換至 settlement 連線池（具備額外預存程序權限），需要滿足：       
      1. left != right                                                                                    
      2. left - right == context.value_b（範圍在 1 ∼ 127 之間）                                           
      3. _bucket(left) == _bucket(right) == context.value_a                                               
  • 突破點：                                                                                              
  在 state.py:31 中定義了 VALUE_EXPONENT = 60。在 IEEE 754 雙精度浮點數（64-bit float，53                 
  位元有效數）中，當數值處於 2⁶⁰ 量級時，相鄰兩個浮點數的間距（ULP, Unit in the Last Place）為 2⁶⁰⁻⁵² =   
  256。                                                                                                   
  這意味著任何在此區間內差值小於 128 的兩個整數，轉型為 float 後會捨入到 完全相同的 64-bit                
  浮點數表示。這使得整數不同但浮點位元完全相同的條件得以成立。                                            
  ──────                                                                                                  
  ### 突破口 4：Gateway 欄位白名單疏漏與 SQL 注入 (Stacked Queries)                                       
                                                                                                          
  • 相關檔案：documents.go:16-37 與 10-views.sql:9-19                                                     
  • 漏洞成因：                                                                                            
      1. 在 Go Gateway 的 documents.go:16 中：                                                            
        var singleKeys = map[string]bool{"a": true, "b": true, "c": true, "d": true}                      
      singleKeys 檢查中 刻意遺漏了 "e"，因此允許 JSON 中出現多個 "e" 物件。                               
      2. Go 的 documents.go:39 只檢查了第一個 "e"（符合 asc|desc 正則），而 Python 的 documents.py:62     
      讀取最後一個 "e"，其中的排序方向 order.get("b", "") 完全沒有在 Python 端受到過濾。                  
      3. 在資料庫端，10-views.sql:9 透過 EXECUTE format(...) 動態拼接 SQL，其中排序表達式直接拼接了       
      direction。                                                                                         
  • 突破點：                                                                                              
  在第二個 "e" 的 b 欄位中，可以利用分號 ; 進行多語句堆疊注入（Stacked SQL                                
  Injection），在資料庫連線會話中執行任意 SQL。                                                           
  ──────                                                                                                  
  ### 突破口 5：PostgreSQL search_path 影子覆蓋與 SUID 提權                                               
                                                                                                          
  • 相關檔案：15-policy.sql:1-16、20-operations.sql:8-25、30-workflows.sql:27-45 與 x.c:5-28              
  • 漏洞成因：                                                                                            
      1. 30-workflows.sql:28 與 15-policy.sql:2 都設定了：                                                
        SET search_path = pg_catalog, pg_temp, public                                                     
      並且在查詢 work_slots 與 __OBJ_B__ 時，皆未加上 public. 前綴。                                      
      2. settlement_reader 角色擁有建立臨時表（TEMPORARY）的權限，且被授予了 30-workflows.sql:45          
      的執行權限。                                                                                        
      3. PostgreSQL 在解析未限定 schema 的物件時，會優先查找 pg_temp。                                    
  • 突破點：                                                                                              
      • 透過 SQL 注入查詢系統目錄（如 pg_proc、pg_constraint）洩漏動態生成的函式名 __OBJ_A__、表名        
      __OBJ_B__ 與常數 __OBJ_C__。                                                                        
      • 建立名為 work_slots 的臨時表，將插槽指針導向 __OBJ_A__()。                                        
      • 建立名為 __OBJ_B__ 的臨時表，將狀態 state 設為 __OBJ_C__。                                        
      • 調用 resolve_work() 時，resolve_action() 讀取到臨時表中的 __OBJ_C__ 並回傳 'run'。                
      • __OBJ_A__()（具備 operator_owner 的 pg_execute_server_program 權限）便會以系統指令執行            
      /usr/local/bin/x 2>&1。                                                                             
      • 由於 /usr/local/bin/x 具有 SUID Root 權限，無參數執行時會直接讀取 /flag.txt，並透過查詢結果返回。 
                                       
