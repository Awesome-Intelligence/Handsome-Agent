# 📱 Mobile Integration

## iOS (Swift)

```swift
class AgentClient {
    private let baseURL = "http://your-server.com"
    
    func ask(_ query: String, completion: @escaping (String?) -> Void) {
        guard let url = URL(string: "\(baseURL)/respond") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["query": query]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, _, _ in
            if let data = data,
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let content = json["content"] as? String {
                DispatchQueue.main.async { completion(content) }
            } else {
                completion(nil)
            }
        }.resume()
    }
}
```

**使用:**
```swift
AgentClient().ask("What is Python?") { answer in
    print(answer ?? "Error")
}
```

## Android (Kotlin)

```kotlin
class AgentClient(private val baseUrl: String = "http://your-server.com") {
    
    suspend fun ask(query: String): String {
        val url = URL("$baseUrl/respond")
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json")
        conn.doOutput = true
        
        conn.outputStream.write("""{"query": "$query"}""".toByteArray())
        
        return conn.inputStream.bufferedReader().readText()
    }
}
```

**使用:**
```kotlin
GlobalScope.launch {
    val answer = AgentClient().ask("What is Python?")
    println(answer)
}
```

## Flutter

```dart
class AgentClient {
    final String baseUrl;
    AgentClient({this.baseUrl = 'http://localhost:8000'});
    
    Future<String> ask(String query) async {
        final resp = await http.post(
            Uri.parse('$baseUrl/respond'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'query': query}),
        );
        
        if (resp.statusCode == 200) {
            final data = jsonDecode(resp.body);
            return data['content'];
        }
        throw Exception('Error: ${resp.statusCode}');
    }
}
```

**使用:**
```dart
final client = AgentClient();
final answer = await client.ask('What is Python?');
print(answer);
```

## React Native

```javascript
const askAgent = async (query) => {
    const response = await fetch('http://your-server/respond', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query})
    });
    
    const data = await response.json();
    return data.content;
}
```

## Unity C#

```csharp
using System.Collections;
using UnityEngine.Networking;

public class AgentClient : MonoBehaviour
{
    private const string BaseURL = "http://your-server.com";
    
    public IEnumerator Ask(string query, System.Action<string> onComplete)
    {
        var request = new UnityWebRequest($"{BaseURL}/respond", "POST");
        request.SetRequestHeader("Content-Type", "application/json");
        request.uploadHandler = new UploadHandlerRaw(
            System.Text.Encoding.UTF8.GetBytes($"{{\"query\": \"{query}\"}}"));
        
        yield return request.SendWebRequest();
        
        if (request.result == UnityWebRequest.Result.Success)
        {
            onComplete?.Invoke(request.downloadHandler.text);
        }
    }
}
```

## 部署检查清单

- [ ] 服务器启动: `python -m gateway --api-key KEY`
- [ ] 健康检查: `curl http://localhost:8000/health`
- [ ] CORS配置: 确保移动端域名在白名单
- [ ] HTTPS: 生产环境务必使用HTTPS
- [ ] 监控: 定期检查 `/stats` 端点
