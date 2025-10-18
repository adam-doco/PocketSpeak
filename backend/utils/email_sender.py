# -*- coding: utf-8 -*-
"""
邮件发送工具 - PocketSpeak V1.3
支持 SMTP / Sendgrid 等邮件服务商
"""

import os
from typing import Optional


def send_verification_code(email: str, code: str) -> bool:
    """
    发送邮箱验证码

    Args:
        email: 收件人邮箱
        code: 6位验证码

    Returns:
        bool: 发送是否成功

    TODO: 接入真实邮件服务商 (Sendgrid / SMTP / 阿里云邮件)
    """
    # 开发环境：打印到控制台
    print("\n" + "=" * 60)
    print("📧 邮件发送模拟")
    print("=" * 60)
    print(f"收件人: {email}")
    print(f"验证码: {code}")
    print(f"有效期: 5 分钟")
    print("=" * 60 + "\n")

    # TODO: 生产环境接入真实邮件服务
    """
    # Sendgrid 示例:
    import sendgrid
    from sendgrid.helpers.mail import Mail

    sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))

    message = Mail(
        from_email='noreply@pocketspeak.com',
        to_emails=email,
        subject='PocketSpeak 验证码',
        html_content=f'<p>您的验证码是: <strong>{code}</strong></p>'
                     f'<p>有效期5分钟，请勿泄露。</p>'
    )

    try:
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"❌ 邮件发送失败: {str(e)}")
        return False
    """

    # 当前返回成功（模拟）
    return True


def send_welcome_email(email: str, username: Optional[str] = None) -> bool:
    """
    发送欢迎邮件

    Args:
        email: 收件人邮箱
        username: 用户名（可选）

    Returns:
        bool: 发送是否成功
    """
    print(f"\n📧 向 {email} 发送欢迎邮件")

    # TODO: 接入真实邮件服务

    return True
