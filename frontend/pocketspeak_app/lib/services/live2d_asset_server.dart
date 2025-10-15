import 'dart:io';
import 'package:flutter/services.dart' show rootBundle;
import 'package:shelf/shelf.dart' as shelf;
import 'package:shelf/shelf_io.dart' as shelf_io;
import 'package:flutter/foundation.dart';

/// Live2D资源本地HTTP服务器
///
/// 由于iOS WebView的安全限制，file://协议无法通过fetch访问其他本地文件
/// 因此我们创建一个本地HTTP服务器来提供Live2D资源
class Live2DAssetServer {
  static Live2DAssetServer? _instance;
  HttpServer? _server;
  int _port = 8765;
  bool _isRunning = false;

  Live2DAssetServer._();

  static Live2DAssetServer get instance {
    _instance ??= Live2DAssetServer._();
    return _instance!;
  }

  bool get isRunning => _isRunning;
  String get baseUrl => 'http://localhost:$_port';

  /// 启动本地HTTP服务器
  Future<void> start() async {
    if (_isRunning) {
      debugPrint('[Live2DAssetServer] 服务器已经在运行');
      return;
    }

    try {
      debugPrint('[Live2DAssetServer] 正在启动本地HTTP服务器...');

      // 创建请求处理器
      final handler = shelf.Pipeline()
          .addMiddleware(shelf.logRequests())
          .addHandler(_handleRequest);

      // 启动服务器
      _server = await shelf_io.serve(
        handler,
        InternetAddress.loopbackIPv4,
        _port,
      );

      _isRunning = true;
      debugPrint('[Live2DAssetServer] ✅ 服务器启动成功: $_baseUrl');
    } catch (e) {
      debugPrint('[Live2DAssetServer] ❌ 服务器启动失败: $e');
      rethrow;
    }
  }

  String get _baseUrl => 'http://${_server!.address.host}:${_server!.port}';

  /// 停止服务器
  Future<void> stop() async {
    if (!_isRunning || _server == null) {
      return;
    }

    await _server!.close(force: true);
    _server = null;
    _isRunning = false;
    debugPrint('[Live2DAssetServer] 服务器已停止');
  }

  /// 处理HTTP请求
  Future<shelf.Response> _handleRequest(shelf.Request request) async {
    try {
      final path = request.url.path;
      debugPrint('[Live2DAssetServer] 请求: $path');

      // URL解码（处理中文文件名）
      final decodedPath = Uri.decodeComponent(path);
      debugPrint('[Live2DAssetServer] 解码后路径: $decodedPath');

      // 构建完整的asset路径
      String assetPath;
      if (decodedPath.isEmpty || decodedPath == '/') {
        assetPath = 'assets/live2d/index.html';
      } else {
        // 移除开头的斜杠
        final cleanPath = decodedPath.startsWith('/') ? decodedPath.substring(1) : decodedPath;

        // 如果路径不是以assets开头，添加assets/live2d/前缀
        if (cleanPath.startsWith('assets/')) {
          assetPath = cleanPath;
        } else {
          assetPath = 'assets/live2d/$cleanPath';
        }
      }

      debugPrint('[Live2DAssetServer] 加载资源: $assetPath');

      // 加载asset
      final data = await rootBundle.load(assetPath);
      final bytes = data.buffer.asUint8List();

      // 确定Content-Type
      final contentType = _getContentType(assetPath);

      return shelf.Response.ok(
        bytes,
        headers: {
          'Content-Type': contentType,
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'no-cache',
        },
      );
    } catch (e) {
      debugPrint('[Live2DAssetServer] ❌ 加载资源失败: $e');
      return shelf.Response.notFound('Resource not found: ${request.url.path}');
    }
  }

  /// 根据文件扩展名确定Content-Type
  String _getContentType(String path) {
    if (path.endsWith('.html')) return 'text/html; charset=utf-8';
    if (path.endsWith('.js')) return 'application/javascript; charset=utf-8';
    if (path.endsWith('.json')) return 'application/json; charset=utf-8';
    if (path.endsWith('.css')) return 'text/css; charset=utf-8';
    if (path.endsWith('.png')) return 'image/png';
    if (path.endsWith('.jpg') || path.endsWith('.jpeg')) return 'image/jpeg';
    if (path.endsWith('.moc3')) return 'application/octet-stream';
    if (path.endsWith('.exp3.json')) return 'application/json; charset=utf-8';
    if (path.endsWith('.motion3.json')) return 'application/json; charset=utf-8';
    if (path.endsWith('.model3.json')) return 'application/json; charset=utf-8';
    if (path.endsWith('.physics3.json')) return 'application/json; charset=utf-8';
    return 'application/octet-stream';
  }
}
