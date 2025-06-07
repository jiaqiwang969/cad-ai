import React, { useEffect, useState } from "react";
import { Table, Spin, Alert } from "antd";

type Props = {
  categoryKey: string;
};

const columns = [
  {
    title: "序号",
    dataIndex: "index",
    key: "index",
    width: 80,
  },
  {
    title: "产品链接",
    dataIndex: "url",
    key: "url",
    render: (text: string) => (
      <a href={text} target="_blank" rel="noopener noreferrer">
        {text.length > 80 ? `${text.substring(0, 80)}...` : text}
      </a>
    ),
  },
];

const ProductTable: React.FC<Props> = ({ categoryKey }) => {
  const [data, setData] = useState<{ key: string; index: number; url: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!categoryKey) return;
    
    console.log(`正在尝试加载产品数据: /products/${categoryKey}.json`);
    setLoading(true);
    setError(null);
    
    fetch(`/products/${categoryKey}.json`)
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 404) {
            throw new Error('NOT_FOUND');
          }
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        // 检查响应的 Content-Type
        const contentType = res.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          throw new Error('INVALID_CONTENT_TYPE');
        }
        
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch (parseError) {
          console.error('JSON 解析失败:', text.substring(0, 200));
          throw new Error('INVALID_JSON');
        }
      })
      .then((arr) => {
        if (!Array.isArray(arr)) {
          throw new Error('INVALID_DATA_FORMAT');
        }
        
        console.log(`成功加载 ${categoryKey} 的产品数据:`, arr.length, "个产品");
        setData(
          arr.map((url, idx) => ({
            key: String(idx),
            index: idx + 1,
            url: String(url),
          }))
        );
        setLoading(false);
      })
      .catch((err) => {
        console.warn(`加载产品数据失败: ${categoryKey}`, err.message);
        
        let errorMessage = '';
        switch (err.message) {
          case 'NOT_FOUND':
            errorMessage = `分类 "${categoryKey}" 暂无产品数据。这可能是一个分类节点，请尝试选择其子节点 (🔖)。`;
            break;
          case 'INVALID_CONTENT_TYPE':
            errorMessage = `服务器返回了非 JSON 格式的数据，可能是 HTML 错误页面。`;
            break;
          case 'INVALID_JSON':
            errorMessage = `服务器返回的数据格式不正确，无法解析为 JSON。`;
            break;
          case 'INVALID_DATA_FORMAT':
            errorMessage = `数据格式错误，期望的是产品链接数组。`;
            break;
          default:
            errorMessage = `加载失败: ${err.message}`;
        }
        
        setError(errorMessage);
        setData([]);
        setLoading(false);
      });
  }, [categoryKey]);

  if (loading) return <Spin tip="加载产品数据中..." />;

  if (error) {
    return (
      <Alert
        message="无法加载产品数据"
        description={error}
        type="warning"
        showIcon
        style={{ margin: '20px 0' }}
        action={
          categoryKey && (
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              💡 提示：只有产品节点 (🔖) 才包含产品数据，分类节点 (📁) 通常不包含直接的产品。
            </div>
          )
        }
      />
    );
  }

  if (data.length === 0 && categoryKey) {
    return (
      <Alert
        message="暂无数据"
        description={`分类 "${categoryKey}" 下暂无产品`}
        type="info"
        showIcon
        style={{ margin: '20px 0' }}
      />
    );
  }

  return (
    <div>
      <p style={{ marginBottom: 16, color: '#666' }}>
        共找到 <strong>{data.length}</strong> 个产品
      </p>
      <Table 
        columns={columns} 
        dataSource={data} 
        pagination={{ 
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`
        }}
      />
    </div>
  );
};

export default ProductTable; 