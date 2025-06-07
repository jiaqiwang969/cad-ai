import React, { useState } from "react";
import { Layout } from "antd";
import CategoryTree from "./components/CategoryTree";
import ProductTable from "./components/ProductTable";

const { Sider, Content } = Layout;

const App: React.FC = () => {
  // 初始状态不选中任何节点，避免加载不存在的产品数据
  const [selectedKey, setSelectedKey] = useState<string>("");

  const handleCategorySelect = (key: string) => {
    console.log("选中的分类 key:", key);
    setSelectedKey(key);
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={320} style={{ background: "#fff", padding: 24 }}>
        <h3>分类树</h3>
        <CategoryTree onSelect={handleCategorySelect} />
      </Sider>
      <Layout>
        <Content style={{ margin: 24, background: "#fff", padding: 24 }}>
          <h3>产品列表 {selectedKey && `(当前分类: ${selectedKey})`}</h3>
          {selectedKey ? (
            <ProductTable categoryKey={selectedKey} />
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '60px 0', 
              color: '#999',
              fontSize: '16px'
            }}>
              👈 请在左侧分类树中选择一个产品节点 (🔖) 查看产品列表
            </div>
          )}
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
