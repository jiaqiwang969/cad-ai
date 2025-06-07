import React, { useEffect, useState, useMemo } from "react";
import { Tree, Spin, Input, Button, Space, Typography } from "antd";
import { SearchOutlined, ExpandAltOutlined, ShrinkOutlined } from "@ant-design/icons";

const { Search } = Input;
const { Text } = Typography;

type TreeNode = {
  title: React.ReactNode;
  key: string;
  children?: TreeNode[];
  isLeaf?: boolean;
  searchText: string;
};

type Props = {
  onSelect: (key: string) => void;
};

const CategoryTree: React.FC<Props> = ({ onSelect }) => {
  const [treeData, setTreeData] = useState<TreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedKeys, setExpandedKeys] = useState<string[]>(['TRACEPARTS_ROOT']);
  const [searchValue, setSearchValue] = useState('');
  const [autoExpandParent, setAutoExpandParent] = useState(true);
  const [selectedKey, setSelectedKey] = useState<string>('');

  // 获取所有节点的key，用于展开所有/收缩所有
  const getAllKeys = (nodes: TreeNode[]): string[] => {
    const keys: string[] = [];
    const traverse = (nodeList: TreeNode[]) => {
      nodeList.forEach(node => {
        keys.push(node.key);
        if (node.children) {
          traverse(node.children);
        }
      });
    };
    traverse(nodes);
    return keys;
  };

  // 搜索逻辑：查找匹配的节点并获取其父节点路径
  const getParentKey = (key: string, tree: TreeNode[]): string => {
    let parentKey = '';
    const traverse = (data: TreeNode[], parent?: string) => {
      data.forEach(item => {
        if (item.key === key) {
          parentKey = parent || '';
        } else if (item.children) {
          traverse(item.children, item.key);
        }
      });
    };
    traverse(tree);
    return parentKey;
  };

  // 收集所有匹配的节点及其父节点
  const getMatchedKeys = (nodes: TreeNode[], searchText: string): string[] => {
    const matchedKeys: string[] = [];
    
    const traverse = (nodeList: TreeNode[], parentKeys: string[] = []) => {
      nodeList.forEach(node => {
        const isMatched = node.searchText.toLowerCase().includes(searchText.toLowerCase());
        
        if (isMatched) {
          // 添加当前节点和所有父节点
          matchedKeys.push(...parentKeys, node.key);
        }
        
        if (node.children) {
          traverse(node.children, [...parentKeys, node.key]);
        }
      });
    };
    
    traverse(nodes);
    return Array.from(new Set(matchedKeys)); // 去重
  };

  // 过滤和高亮搜索结果
  const filteredTreeData = useMemo(() => {
    if (!searchValue) return treeData;

    const loop = (data: TreeNode[]): TreeNode[] =>
      data.map(item => {
        const index = item.searchText.toLowerCase().indexOf(searchValue.toLowerCase());
        
        let title = item.title;
        if (index > -1) {
          // 重新构建带高亮的标题
          const hasChildren = item.children && item.children.length > 0;
          const icon = hasChildren ? '📁' : '🔖';
          const textColor = hasChildren ? '#666' : '#1890ff';
          const fontWeight = hasChildren ? 'normal' : '500';
          
          const beforeStr = item.searchText.substring(0, index);
          const matchStr = item.searchText.substring(index, index + searchValue.length);
          const afterStr = item.searchText.substring(index + searchValue.length);
          
          title = (
            <span style={{ fontSize: hasChildren ? '13px' : '14px' }}>
              <span style={{ marginRight: '6px' }}>{icon}</span>
              <span style={{ fontWeight, color: textColor }}>
                {beforeStr}
                <span style={{ color: '#f50', backgroundColor: '#ffd591' }}>{matchStr}</span>
                {afterStr}
              </span>
            </span>
          );
        }

        if (item.children) {
          return { ...item, title, children: loop(item.children) };
        }
        return { ...item, title };
      });

    return loop(treeData);
  }, [treeData, searchValue]);

  useEffect(() => {
    fetch("/classification_tree.json")
      .then((res) => res.json())
      .then((data) => {
        console.log("加载的分类树数据：", data);
        
        // 转换后端结构为 antd Tree 结构
        const convert = (node: any): TreeNode => {
          if (!node.code) {
            console.warn("节点缺少 code 字段：", node);
            return {
              title: node.name || "未知节点",
              key: `unknown_${Math.random()}`,
              children: node.children?.map(convert) || [],
              searchText: node.name || "未知节点",
            };
          }
          
          const hasChildren = node.children && node.children.length > 0;
          let icon = '';
          let textColor = '';
          let fontWeight = '';
          
          if (hasChildren) {
            icon = '📁';
            textColor = '#666';
            fontWeight = 'normal';
          } else {
            icon = '🔖';
            textColor = '#1890ff';
            fontWeight = '500';
          }
          
          const displayTitle = (
            <span style={{ fontSize: hasChildren ? '13px' : '14px' }}>
              <span style={{ marginRight: '6px' }}>{icon}</span>
              <span style={{ fontWeight, color: textColor }}>{node.name}</span>
            </span>
          );
          
          return {
            title: displayTitle,
            key: node.code,
            children: node.children?.map(convert) || [],
            isLeaf: !hasChildren,
            searchText: node.name,
          };
        };
        
        if (data.root) {
          const convertedData = [convert(data.root)];
          setTreeData(convertedData);
          
          // 自动展开前2-3层，方便用户浏览
          const autoExpandKeys = ['TRACEPARTS_ROOT'];
          if (data.root.children) {
            data.root.children.forEach((child: any) => {
              autoExpandKeys.push(child.code);
            });
          }
          setExpandedKeys(autoExpandKeys);
        } else {
          console.error("JSON 结构错误，未找到 root 字段");
          setTreeData([]);
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error("加载分类树失败：", error);
        setLoading(false);
      });
  }, []);

  // 搜索逻辑
  const onSearch = (value: string) => {
    setSearchValue(value);
    if (value) {
      const matchedKeys = getMatchedKeys(treeData, value);
      setExpandedKeys(matchedKeys);
    } else {
      // 搜索清空时恢复默认展开状态
      setExpandedKeys(['TRACEPARTS_ROOT']);
    }
    setAutoExpandParent(true);
  };

  // 展开所有
  const expandAll = () => {
    const allKeys = getAllKeys(treeData);
    setExpandedKeys(allKeys);
  };

  // 收缩所有（只保留根节点）
  const collapseAll = () => {
    setExpandedKeys(['TRACEPARTS_ROOT']);
  };

  if (loading) return <Spin tip="加载分类树中..." />;

  return (
    <div>
      {/* 搜索和操作区域 */}
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
        <Search
          placeholder="搜索分类..."
          onSearch={onSearch}
          onChange={(e) => onSearch(e.target.value)}
          style={{ width: '100%' }}
          prefix={<SearchOutlined />}
          allowClear
        />
        
        <Space>
          <Button 
            size="small" 
            icon={<ExpandAltOutlined />}
            onClick={expandAll}
            title="展开所有"
          >
            展开
          </Button>
          <Button 
            size="small" 
            icon={<ShrinkOutlined />}
            onClick={collapseAll}
            title="收缩所有"
          >
            收缩
          </Button>
        </Space>
        
        <div style={{ fontSize: '11px', color: '#999', lineHeight: '16px' }}>
          <div>📁 分类节点 | 🔖 产品节点</div>
          {selectedKey && (
            <div style={{ marginTop: '4px' }}>
              <Text type="secondary">当前: {selectedKey}</Text>
            </div>
          )}
          {searchValue && (
            <div style={{ marginTop: '4px', color: '#1890ff' }}>
              🔍 搜索: "{searchValue}"
            </div>
          )}
        </div>
      </Space>

      {/* 分类树 */}
      <Tree
        treeData={filteredTreeData}
        expandedKeys={expandedKeys}
        autoExpandParent={autoExpandParent}
        selectedKeys={selectedKey ? [selectedKey] : []}
        onExpand={(keys) => {
          setExpandedKeys(keys as string[]);
          setAutoExpandParent(false);
        }}
        onSelect={(selectedKeys) => {
          if (selectedKeys.length > 0) {
            const key = selectedKeys[0] as string;
            console.log("用户点击了节点:", key);
            setSelectedKey(key);
            
            // 查找节点信息以提供更好的用户反馈
            const findNode = (nodes: TreeNode[], targetKey: string): TreeNode | null => {
              for (const node of nodes) {
                if (node.key === targetKey) return node;
                if (node.children) {
                  const found = findNode(node.children, targetKey);
                  if (found) return found;
                }
              }
              return null;
            };
            
            const selectedNode = findNode(treeData, key);
            if (selectedNode && selectedNode.isLeaf) {
              console.log("✅ 用户选择了产品节点，将加载产品列表");
            } else {
              console.log("ℹ️ 用户选择了分类节点，可能无产品数据");
            }
            
            onSelect(key);
          }
        }}
        style={{ 
          width: '100%',
          fontSize: '13px',
          maxHeight: 'calc(100vh - 300px)',
          overflowY: 'auto'
        }}
      />
    </div>
  );
};

export default CategoryTree; 