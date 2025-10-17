import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'dart:convert';
import '../services/live2d_asset_server.dart';

/// Live2D控制器 - 提供对外的控制接口
class Live2DController {
  InAppWebViewController? _webViewController;
  bool _isInitialized = false;

  Live2DController();

  bool get isInitialized => _isInitialized;

  void _setWebViewController(InAppWebViewController controller) {
    _webViewController = controller;
  }

  void _setInitialized(bool value) {
    _isInitialized = value;
  }

  /// 播放动作
  Future<void> playMotion(String group, int index) async {
    if (!_isInitialized || _webViewController == null) {
      debugPrint('[Live2DController] Live2D未初始化，无法播放动作');
      return;
    }

    try {
      await _webViewController!.evaluateJavascript(
        source: 'window.playMotion("$group", $index);'
      );
      debugPrint('[Live2DController] 播放动作: group="$group", index=$index');
    } catch (e) {
      debugPrint('[Live2DController] 播放动作失败: $e');
    }
  }

  /// 播放表情
  Future<void> playExpression(String name) async {
    if (!_isInitialized || _webViewController == null) {
      debugPrint('[Live2DController] Live2D未初始化，无法播放表情');
      return;
    }

    try {
      await _webViewController!.evaluateJavascript(
        source: 'window.playExpression("$name");'
      );
      debugPrint('[Live2DController] 播放表情: $name');
    } catch (e) {
      debugPrint('[Live2DController] 播放表情失败: $e');
    }
  }

  /// 播放待机动作
  Future<void> playIdle() async {
    await playMotion('', 0);
  }

  /// 播放开心动作
  Future<void> playHappy() async {
    await playMotion('', 2);
    await playExpression('A1爱心眼');
  }

  /// 播放惊讶动作
  Future<void> playSurprised() async {
    await playMotion('', 1);
    await playExpression('A3星星眼');
  }

  /// 播放生气动作
  Future<void> playAngry() async {
    await playMotion('', 3);
    await playExpression('A2生气');
  }

  /// 🔥 启动嘴部同步动画
  Future<void> startLipSync() async {
    if (!_isInitialized || _webViewController == null) {
      debugPrint('[Live2DController] Live2D未初始化，无法启动嘴部同步');
      return;
    }

    try {
      await _webViewController!.evaluateJavascript(
        source: 'window.startLipSync();'
      );
      debugPrint('[Live2DController] 启动嘴部同步动画');
    } catch (e) {
      debugPrint('[Live2DController] 启动嘴部同步失败: $e');
    }
  }

  /// 🔥 停止嘴部同步动画
  Future<void> stopLipSync() async {
    if (!_isInitialized || _webViewController == null) {
      debugPrint('[Live2DController] Live2D未初始化，无法停止嘴部同步');
      return;
    }

    try {
      await _webViewController!.evaluateJavascript(
        source: 'window.stopLipSync();'
      );
      debugPrint('[Live2DController] 停止嘴部同步动画');
    } catch (e) {
      debugPrint('[Live2DController] 停止嘴部同步失败: $e');
    }
  }
}

/// Live2D模型显示组件
///
/// 使用InAppWebView加载Live2D模型，提供动作和表情控制接口
class Live2DWidget extends StatefulWidget {
  final Function(Live2DController)? onControllerCreated;

  const Live2DWidget({
    super.key,
    this.onControllerCreated,
  });

  @override
  State<Live2DWidget> createState() => _Live2DWidgetState();
}

class _Live2DWidgetState extends State<Live2DWidget> {
  final Live2DController _live2dController = Live2DController();
  String _status = '正在初始化...';

  @override
  void initState() {
    super.initState();
    _initServer();
    // 延迟通知控制器创建，避免build期间调用setState
    if (widget.onControllerCreated != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.onControllerCreated!(_live2dController);
      });
    }
  }

  /// 初始化本地HTTP服务器
  Future<void> _initServer() async {
    try {
      final server = Live2DAssetServer.instance;
      if (!server.isRunning) {
        await server.start();
      }
    } catch (e) {
      debugPrint('[Live2DWidget] 服务器启动失败: $e');
      setState(() {
        _status = '服务器启动失败: $e';
      });
    }
  }

  @override
  void dispose() {
    // 注意：不要在这里停止服务器，因为可能有其他页面在使用
    super.dispose();
  }

  /// 处理来自WebView的消息
  void _handleMessageFromWebView(String message) {
    try {
      final data = jsonDecode(message);
      final type = data['type'];

      switch (type) {
        case 'initialized':
          final status = data['status'];
          if (status == 'success') {
            setState(() {
              _live2dController._setInitialized(true);
              _status = 'Live2D已就绪';
            });
            debugPrint('[Live2DWidget] Live2D初始化成功');
          } else {
            setState(() {
              _live2dController._setInitialized(false);
              _status = 'Live2D初始化失败: ${data['message'] ?? '未知错误'}';
            });
            debugPrint('[Live2DWidget] Live2D初始化失败: ${data['message']}');
          }
          break;

        case 'log':
          final level = data['level'] ?? 'info';
          final logMessage = data['message'];
          debugPrint('[Live2D $level] $logMessage');
          break;

        default:
          debugPrint('[Live2DWidget] 未知消息类型: $type');
      }
    } catch (e) {
      debugPrint('[Live2DWidget] 消息解析失败: $message, 错误: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // InAppWebView显示Live2D模型
        InAppWebView(
          initialSettings: InAppWebViewSettings(
            javaScriptEnabled: true,
            allowFileAccessFromFileURLs: true,  // 关键设置：允许file://访问其他file://
            allowUniversalAccessFromFileURLs: true,  // 关键设置：允许跨域访问
            transparentBackground: true,
            useOnLoadResource: true,
          ),
          onWebViewCreated: (controller) async {
            _live2dController._setWebViewController(controller);

            // 添加JavaScript消息处理器
            controller.addJavaScriptHandler(
              handlerName: 'FlutterChannel',
              callback: (args) {
                if (args.isNotEmpty) {
                  _handleMessageFromWebView(args[0].toString());
                }
              },
            );

            // 等待服务器启动
            await _initServer();

            // 通过本地HTTP服务器加载页面
            final server = Live2DAssetServer.instance;
            final url = '${server.baseUrl}/';
            debugPrint('[Live2DWidget] 加载URL: $url');

            await controller.loadUrl(
              urlRequest: URLRequest(url: WebUri(url)),
            );
          },
          onLoadStart: (controller, url) {
            debugPrint('[Live2DWidget] 页面开始加载: $url');
          },
          onLoadStop: (controller, url) {
            debugPrint('[Live2DWidget] 页面加载完成: $url');
          },
          onLoadError: (controller, url, code, message) {
            debugPrint('[Live2DWidget] 页面加载错误: $message');
            setState(() {
              _status = '页面加载失败: $message';
            });
          },
          onConsoleMessage: (controller, consoleMessage) {
            debugPrint('[WebView Console] ${consoleMessage.message}');
          },
        ),

        // 调试状态显示（可选）
        if (!_live2dController.isInitialized)
          Positioned(
            bottom: 20,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _status,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
      ],
    );
  }
}
