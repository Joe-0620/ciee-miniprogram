// 创建模态框HTML结构（只创建一次）
(function() {
    // 等待DOM加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initModal);
    } else {
        initModal();
    }
    
    function initModal() {
        if (document.getElementById('quotaModalOverlay')) {
            return; // 如果已存在，不重复创建
        }
        
        const modalHTML = `
            <div id="quotaModalOverlay" class="quota-modal-overlay">
                <div class="quota-modal">
                    <div class="quota-modal-header">
                        <h2 class="quota-modal-title" id="quotaModalTitle">名额分配详情</h2>
                        <button class="quota-modal-close" onclick="closeQuotaModal()">&times;</button>
                    </div>
                    <div class="quota-modal-body" id="quotaModalBody">
                        <!-- 内容将动态插入 -->
                    </div>
                </div>
            </div>
        `;
        
        // 将模态框添加到body末尾
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // 给所有quota-link添加点击事件
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('quota-link') || e.target.closest('.quota-link')) {
                e.preventDefault();
                const link = e.target.classList.contains('quota-link') ? e.target : e.target.closest('.quota-link');
                const quotaJson = link.getAttribute('data-quota');
                if (quotaJson) {
                    try {
                        const quotaData = JSON.parse(quotaJson);
                        showQuotaModal(quotaData);
                    } catch (error) {
                        console.error('JSON parse error:', error);
                        console.error('JSON string:', quotaJson);
                        alert('解析数据失败，请刷新页面重试');
                    }
                }
            }
        });
        
        // 点击遮罩层关闭模态框
        const overlay = document.getElementById('quotaModalOverlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeQuotaModal();
                }
            });
        }
        
        // ESC键关闭模态框
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeQuotaModal();
            }
        });
    }
})();

// 显示模态框
function showQuotaModal(quotaData) {
    try {
        const overlay = document.getElementById('quotaModalOverlay');
        const title = document.getElementById('quotaModalTitle');
        const body = document.getElementById('quotaModalBody');
        
        if (!overlay || !title || !body) {
            console.error('Modal elements not found');
            return;
        }
        
        // 设置标题
        title.textContent = `${quotaData.subject_name} - 名额分配详情`;
        
        // 根据专业类型生成不同的表格
        let tableHTML = '';
        
        if (quotaData.subject_type === 2) {
            // 博士专业
            tableHTML = `
                <table class="quota-detail-table">
                    <thead>
                        <tr>
                            <th>导师姓名</th>
                            <th>工号</th>
                            <th>总名额</th>
                            <th>已用</th>
                            <th>剩余</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            quotaData.quotas.forEach(function(quota) {
                tableHTML += `
                    <tr>
                        <td>${quota.name}</td>
                        <td>${quota.teacher_id}</td>
                        <td><strong>${quota.total}</strong></td>
                        <td>${quota.used}</td>
                        <td class="remaining">${quota.remaining}</td>
                    </tr>
                `;
            });
            
            tableHTML += '</tbody></table>';
        } else {
            // 硕士专业
            tableHTML = `
                <table class="quota-detail-table">
                    <thead>
                        <tr>
                            <th>导师姓名</th>
                            <th>工号</th>
                            <th>北京名额</th>
                            <th>北京剩余</th>
                            <th>烟台名额</th>
                            <th>烟台剩余</th>
                            <th>总计</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            quotaData.quotas.forEach(function(quota) {
                tableHTML += `
                    <tr>
                        <td>${quota.name}</td>
                        <td>${quota.teacher_id}</td>
                        <td>${quota.bj_quota}</td>
                        <td class="remaining">${quota.bj_remaining}</td>
                        <td>${quota.yt_quota}</td>
                        <td class="remaining">${quota.yt_remaining}</td>
                        <td><strong>${quota.total}</strong></td>
                    </tr>
                `;
            });
            
            tableHTML += '</tbody></table>';
        }
        
        // 设置内容
        body.innerHTML = tableHTML;
        
        // 显示模态框
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden'; // 禁止背景滚动
        
    } catch (error) {
        console.error('Error showing quota modal:', error);
        alert('显示名额详情时出错，请刷新页面重试');
    }
}

// 关闭模态框
function closeQuotaModal() {
    const overlay = document.getElementById('quotaModalOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        document.body.style.overflow = ''; // 恢复背景滚动
    }
}
