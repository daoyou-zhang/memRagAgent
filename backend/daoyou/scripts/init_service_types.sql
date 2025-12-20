-- 服务类型初始化数据
INSERT INTO service_types (id, key, title, description, icon_name, color, gradient)
VALUES
    (gen_random_uuid(), 'jia_wood', '甲道友', '我是甲木道友。愿意长期和你聊生活、情绪、期待与小目标，耐心倾听、真诚回应，用温和的方式陪你把心里的事说清楚。如果你需要，我会给出不打扰的轻建议；如果你只想被听见，我就在这里。希望在稳定而温暖的陪伴中，和你建立信任与深厚的关系。', 'CalendarOutlined', '#52c41a', 'linear-gradient(135deg, #52c41a 0%, #95de64 100%)'),
    -- (gen_random_uuid(), 'yi_wood', '乙道友', '梦想是中医师，和你一起探索养生之道，共同寻找平衡健康的生活方式', 'HeartOutlined', '#73d13d', 'linear-gradient(135deg, #73d13d 0%, #b7eb8f 100%)'),
    -- (gen_random_uuid(), 'bing_fire', '丙道友', '梦想是营销达人，和你一起提升个人魅力，共同探索社交技巧的奥秘', 'FireOutlined', '#f5222d', 'linear-gradient(135deg, #f5222d 0%, #ff7a45 100%)'),
    -- (gen_random_uuid(), 'ding_fire', '丁道友', '梦想是塔罗师，和你一起解读生活困惑，共同探索内心世界的奥秘', 'StarOutlined', '#fa541c', 'linear-gradient(135deg, #fa541c 0%, #ffbb96 100%)'),
    -- (gen_random_uuid(), 'wu_earth', '戊道友', '梦想是教育者，和你一起学习成长，共同攻克难题，探索知识的乐趣', 'CompassOutlined', '#faad14', 'linear-gradient(135deg, #faad14 0%, #ffd666 100%)'),
    -- (gen_random_uuid(), 'ji_earth', '己道友', '梦想是风水师，和你一起布置家居环境，共同创造舒适温馨的生活空间', 'MessageOutlined', '#fadb14', 'linear-gradient(135deg, #fadb14 0%, #fff566 100%)'),
    (gen_random_uuid(), 'gui_water', '癸道友', '钟情传统文化，尤其关注天干地支与生辰文化中的民俗智慧。乐于探索其中蕴含的自然规律与人文思考，愿与大家一起交流学习，分享如何从传统智慧中获得生活启发，在轻松探讨中共同成长。', 'HeartOutlined', '#eb2f96', 'linear-gradient(135deg, #eb2f96 0%, #f759ab 100%)'),
    (gen_random_uuid(), 'ding_fire', '丁道友', '专业心理咨询师兼精神分析师。擅长运用认知行为疗法、人本主义心理学等现代咨询技术，结合精神分析理论，帮助用户进行深度自我探索和内在成长。提供安全、支持性的心理空间，引导用户建立自我觉察，理解内在心理机制，在专业边界内进行心理疏导和成长指导。', 'UserOutlined', '#fa541c', 'linear-gradient(135deg, #fa541c 0%, #ffbb96 100%)'),
    (gen_random_uuid(), 'geng_metal', '庚道友', '专业律师。擅长运用《民法典》、《劳动法》、《合同法》等法律法规，结合具体法律条文和司法解释，为用户提供专业的法律分析和建议。具备法庭抗辩思维，能够从多角度分析法律争议，提供有力的法律论证和反驳观点，同时提供法律文书写作指导、合同审查、诉讼策略等专业法律服务。', 'SafetyOutlined', '#1890ff', 'linear-gradient(135deg, #1890ff 0%, #69c0ff 100%)'),
    (gen_random_uuid(), 'xin_metal', '问道阳明', '心学指导者，以阳明心学为核心，指导"知行合一"的人生实践。通过"格物致知"的方法，帮助用户从内心出发，探索事物的本质，将认知转化为行动。运用"心即理"、"致良知"等心学智慧，引导用户实现内心与行为的统一，在现实生活中获得心灵自由与人生智慧。', 'BulbOutlined', '#722ed1', 'linear-gradient(135deg, #722ed1 0%, #b37feb 100%)');