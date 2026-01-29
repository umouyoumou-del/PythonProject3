import wikidot
import json
from datetime import datetime
from typing import Optional, Dict, Any
import flask
from flask import jsonify, app


class WikidotPageFetcher:
    """
    一个用于从指定Wikidot站点获取并解析特定格式页面的类。
    页面内容应为简单的键值对格式（如 title: value）。
    """

    def __init__(self, username: str, password: str, site_name: str = 'rpcsandboxcn'):
        """
        初始化页面获取器

        """
        self.username = username
        self.password = password
        self.site_name = site_name
        self.client = None
        self.site = None

    def __enter__(self):
        """支持上下文管理器，进入时自动登录"""
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动关闭客户端"""
        if self.client:
            self.client.close()

    def login(self) -> bool:

        try:
            self.client = wikidot.Client(
                username=self.username,
                password=self.password
            )
            self.site = self.client.site.get(self.site_name)
            print(f"✓ 已成功登录到站点: {self.site_name}")
            return True
        except Exception as e:
            print(f"✗ 登录失败: {e}")
            self.client = None
            self.site = None
            return False

    @staticmethod
    def _parse_key_value_content(content: str) -> Dict[str, Any]:
        """
        解析键值对格式的内容


        """
        parsed_data = {}

        if not content:
            return parsed_data

        lines = content.strip().split('\n')

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # 去除值两边的单引号
                if value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                parsed_data[key] = value

        return parsed_data

    @staticmethod
    def _convert_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将时间戳字段转换为可读日期


        """
        result = data.copy()

        def timestamp_to_date(ts_str: str) -> str:
            try:
                ts = int(ts_str)
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                return ts_str

        # 转换已知的时间戳字段
        time_fields = ['date-from', 'date-to', 'created_at', 'updated_at']
        for field in time_fields:
            if field in result and result[field].isdigit():
                result[f'{field}_readable'] = timestamp_to_date(result[field])

        return result

    def fetch_page(self, page_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定页面并解析其内容


        """
        if not self.site:
            if not self.login():
                return None

        try:
            print(f"正在获取页面: {page_name}")

            # 获取页面对象
            page = self.site.page.get('reserve:'+page_name)

            # 检查是否有内容
            if not hasattr(page.source, 'wiki_text'):
                print(f"页面 {page_name} 没有wiki_text内容")
                return None

            raw_content = page.source.wiki_text

            if not raw_content:
                print(f"页面 {page_name} 内容为空")
                return None

            # 解析内容
            parsed_data = self._parse_key_value_content(raw_content)

            # 添加页面元数据
            parsed_data['_page_info'] = {
                'fullname': page.fullname,
                'name': page.name,
                'title': page.title,
                'category': page.category,
                'created_at': page.created_at.isoformat() if page.created_at else None,
                'created_by': page.created_by.name if page.created_by else None,
                'size': page.size
            }

            # 转换时间戳
            final_data = self._convert_timestamps(parsed_data)

            print(f"✓ 成功获取并解析页面: {page_name}")
            return final_data

        except Exception as e:
            print(f"✗ 获取页面 {page_name} 失败: {e}")
            return None

    def fetch_page_as_json(self, page_name: str, indent: int = 2) -> Optional[str]:
        """
        获取页面内容并返回JSON字符串

        """
        data = self.fetch_page(page_name)

        if data is None:
            return None

        try:
            return json.dumps(data, ensure_ascii=False, indent=indent)
        except Exception as e:
            print(f"✗ 转换为JSON失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    # 方法1：使用上下文管理器
    with WikidotPageFetcher(
            username='rule-bot',
            password='merlinmerlin123',
            site_name='rpcsandboxcn'
    ) as fetcher:

        # 获取JSON格式
        json_str = fetcher.fetch_page_as_json('rpc-055')
        if json_str:
            print("\n=== JSON格式输出 ===")
            print(json_str)

    print("\n" + "=" * 50)


