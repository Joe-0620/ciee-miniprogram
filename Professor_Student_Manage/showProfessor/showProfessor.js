// pages/showProfessor/showProfessor.js
import Dialog from '@vant/weapp/dialog/dialog';
const config = require('../../utils/config.js');
Page({
  /**
   * 页面的初始数据
   */
  data: {
    dialogShow: false,
    usertype: '',
    isTriggered: false,
    refreshText: '下拉刷新',
    activeKey: 0,
    active: 0,
    departmentList: '',
    professorList: '',
    selectedTeacherId:'',//当前查看的老师id
    professorId: [],
    show: false,
    show1: false,//展示弹框
    show2:false,
    selectedValue: [],
    isPopupOpen: true,
    checked:true,
    open_time: '',
    close_time: '',
    // 新增分页相关字段
    currentPage: 1,
    pageSize: 10,
    hasNextPage: false,
    isLoadingMore: false,
    selectedDepartmentId: null, // 当前选中的方向ID
    // 新增搜索相关字段
    searchKeyword: '',
    isSearchMode: false, // 是否在搜索模式
    searchResultCount: 0, // 搜索结果数量
    
    // 新增筛选相关字段
    showFilterPopup: false, // 是否显示筛选弹窗
    masterSubjects: [], // 所有硕士专业列表
    doctorSubjects: [], // 所有博士专业列表
    selectedMasterSubject: null, // 已选择的硕士专业ID（单选）
    selectedDoctorSubject: null, // 已选择的博士专业ID（单选）
    isFilterMode: false, // 是否在筛选模式
    filterType: '', // 'master' 或 'doctor'
    filterSubjectName: '', // 筛选的专业名称
    filteredProfessorsByDept: {}, // 按方向分组的筛选结果缓存
  },
  getMessage() {
    // console.log("getmessage")
    wx.requestSubscribeMessage({
      tmplIds: ['S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs'],
      success (res) {
        // console.log(res)
        const templateId = 'S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs';
        if (res[templateId] === "accept") {
          wx.showToast({
            title: '订阅一次成功',
            icon: 'success',
            duration: 2000,
          });
        } else if (res[templateId] === "reject") {
          wx.showToast({
            title: '未订阅',
            icon: 'error',
            duration: 2000,
          });
        }
       }
    })
  },
  //选择导师弹框确认按钮
  showAlertDialog(e) {
    const professor_id = e.currentTarget.dataset.pid;
    const professor_name = e.currentTarget.dataset.pname;
    const token = wx.getStorageSync('token');
    this.setData({
      professorId: professor_id,
    });
    this.getMessage();
   // 异步请求
    const beforeClose = (action) =>
      new Promise((resolve) => {
        if (action === 'confirm') {
          setTimeout(() => {
            // 封装为 Promise
            const requestPromise = new Promise((resolve, reject) => {
              wx.request({
                url: `${config.BASE_URL}/Select_Information/select-professor/`,
                method: 'POST',
                data: {
                  professor_id: professor_id,
                },
                header:{
                  Authorization:`Token ${token}`
                },
                success: res => {
                  resolve({statusCode: res.statusCode, message: res.data.message});
                },
                fail: err => {
                  console.error('数据提交失败：', err);
                  reject(err);
                }
              });
            });
            requestPromise.then(({statusCode, message}) => {
              // 根据 statusCode 进行处理
              // wx.showToast({
              //   title: `${message}`,
              //   icon: 'success',
              //   duration: 2000,
              // });
              wx.showModal({
                // title: '', // 对话框标题
                content: `${message}`, // 对话框内容
                showCancel: false,
                success (res) {
                  if (res.confirm) {
                    // console.log('用户点击确定')
                  }
                }
              })
              // if (statusCode === 201) {
              //   // 选择成功
              //   wx.showToast({
              //     title: '提交选择成功',
              //     icon: 'success',
              //     duration: 2000,
              //   });
              // } else if (statusCode === 405) {
              //   wx.showToast({
              //     title: '已完成导师选择',
              //     icon: 'error',
              //     duration: 2000,
              //   });
              //   // 这里可以放置状态码为 409 的逻辑
              // } else if (statusCode === 409) {
              //   wx.showToast({
              //     title: '已有待回复请求',
              //     icon: 'error',
              //     duration: 2000,
              //   });
              //   // 这里可以放置状态码为 409 的逻辑
              // } else if (statusCode === 400) {
              //   // wx.showToast({
              //   //   title: `${message}`,
              //   //   icon: 'error',
              //   //   duration: 2000,
              //   // });
              //   wx.showModal({
              //     title: '选择失败', // 对话框标题
              //     content: `${message}`, // 对话框内容
              //     showCancel: false,
              //     success (res) {
              //       if (res.confirm) {
              //         // console.log('用户点击确定')
              //       }
              //     }
              //   })
              //   // 这里可以放置状态码为 400 的逻辑
              // } else if (statusCode === 404) {
              //   wx.showToast({
              //     title: '导师不存在',
              //     icon: 'error',
              //     duration: 2000,
              //   });
              //   // 这里可以放置状态码为 500 的逻辑
              // } else if (statusCode === 401) {
              //   wx.showToast({
              //     title: '导师无名额',
              //     icon: 'error',
              //     duration: 2000,
              //   });
              //   // 这里可以放置状态码为 500 的逻辑
              // }else if (statusCode === 500) {
              //   wx.showToast({
              //     title: '请重试',
              //     icon: 'error',
              //     duration: 2000,
              //   });
              //   // 这里可以放置状态码为 401 的逻辑
              // }
              // ... 其他状态码的逻辑
            }).catch(() => {
            });
            resolve(true);
          }, 1000);
        } else {
          // 立刻关闭弹窗
          resolve(true);
        }
      });
    Dialog.confirm({
      title: `请确认你的选择是 ${professor_name} 老师`,
      message: '选择成功后只有被退回或撤销后才能重新进行导师选择，在此期间请耐心等待。',
      beforeClose,
    })
    .then((shouldCloseDialog) => {
      if (shouldCloseDialog) {
        this.setData({
          show2: false,
        });
      }
    })
    .catch(() => {
      
      // 在取消操作后立刻关闭弹窗
      this.setData({
        show2: false,
      });
    });
  },

  showPopup(e) {
    const professor_id = e.currentTarget.dataset.pid;
    this.setData({ 
      show: true,
      selectedTeacherId: professor_id,
    });
  },

  onClose() {
    this.setData({ 
      show: false,
    });
  },

  // 新增：搜索导师
  onSearchChange(e) {
    this.setData({
      searchKeyword: e.detail
    });
  },

  // 新增：执行搜索
  onSearch() {
    const keyword = this.data.searchKeyword.trim();
    
    if (!keyword) {
      wx.showToast({
        title: '请输入搜索关键词',
        icon: 'none'
      });
      return;
    }

    // 进入搜索模式
    this.setData({
      isSearchMode: true,
      currentPage: 1,
      professorList: [],
      selectedDepartmentId: null // 搜索时不限定方向
    }, () => {
      this.loadProfessors(false);
    });
  },

  // 新增：取消搜索
  onSearchCancel() {
    this.setData({
      searchKeyword: '',
      isSearchMode: false,
      currentPage: 1,
      professorList: []
    }, () => {
      // 恢复到第一个方向
      const firstDepartmentId = this.data.departmentList && this.data.departmentList.length > 0 
        ? this.data.departmentList[0].id 
        : null;
      this.setData({
        selectedDepartmentId: firstDepartmentId,
        active: 0
      }, () => {
        this.loadProfessors(false);
      });
    });
  },

  // 新增：清空搜索
  onSearchClear() {
    this.setData({
      searchKeyword: ''
    });
  },

  // 新增：显示筛选弹窗
  showFilterPopup() {
    // 如果还没有加载专业列表，先加载
    if (this.data.masterSubjects.length === 0 && this.data.doctorSubjects.length === 0) {
      this.loadSubjectsForFilter();
    }
    this.setData({
      showFilterPopup: true
    });
  },

  // 新增：关闭筛选弹窗
  closeFilterPopup() {
    this.setData({
      showFilterPopup: false
    });
  },

  // 新增：加载专业列表
  loadSubjectsForFilter() {
    wx.request({
      url: `${config.BASE_URL}/Professor_Student_Manage/subjects-for-filter/`,
      method: 'GET',
      success: (res) => {
        this.setData({
          masterSubjects: res.data.master_subjects,
          doctorSubjects: res.data.doctor_subjects
        });
      },
      fail: (err) => {
        console.error('获取专业列表失败：', err);
        wx.showToast({
          title: '加载专业列表失败',
          icon: 'none'
        });
      }
    });
  },

  // 新增：硕士专业选择变化
  onMasterSubjectChange(e) {
    console.log('硕士专业选择变化', e.detail);
    const subjectId = typeof e.detail === 'number' ? e.detail : (e.detail ? parseInt(e.detail) : null);
    console.log('解析后的硕士专业ID', subjectId);
    this.setData({
      selectedMasterSubject: subjectId,
      selectedDoctorSubject: null // 选择硕士专业时清空博士专业
    });
  },

  // 新增：博士专业选择变化
  onDoctorSubjectChange(e) {
    console.log('博士专业选择变化', e.detail);
    const subjectId = typeof e.detail === 'number' ? e.detail : (e.detail ? parseInt(e.detail) : null);
    console.log('解析后的博士专业ID', subjectId);
    this.setData({
      selectedDoctorSubject: subjectId,
      selectedMasterSubject: null // 选择博士专业时清空硕士专业
    });
  },

  // 新增：点击专业单元格时触发选择
  onSubjectCellClick(e) {
    const subjectId = parseInt(e.currentTarget.dataset.id);
    const type = e.currentTarget.dataset.type;
    
    console.log('点击专业单元格', { subjectId, type });
    
    if (type === 'master') {
      // 如果点击的是已选中的，不做处理；否则选中它
      if (this.data.selectedMasterSubject === subjectId) {
        return;
      }
      this.setData({
        selectedMasterSubject: subjectId,
        selectedDoctorSubject: null
      });
    } else if (type === 'doctor') {
      // 如果点击的是已选中的，不做处理；否则选中它
      if (this.data.selectedDoctorSubject === subjectId) {
        return;
      }
      this.setData({
        selectedDoctorSubject: subjectId,
        selectedMasterSubject: null
      });
    }
  },

  // 新增：确认筛选
  confirmFilter() {
    console.log('开始确认筛选，当前状态：', {
      selectedMasterSubject: this.data.selectedMasterSubject,
      selectedDoctorSubject: this.data.selectedDoctorSubject,
      masterSubjects: this.data.masterSubjects,
      doctorSubjects: this.data.doctorSubjects
    });
    
    const hasMaster = this.data.selectedMasterSubject !== null;
    const hasDoctor = this.data.selectedDoctorSubject !== null;

    if (!hasMaster && !hasDoctor) {
      wx.showToast({
        title: '请选择一个专业',
        icon: 'none'
      });
      return;
    }

    // 确定筛选类型
    const filterType = hasMaster ? 'master' : 'doctor';
    const selectedId = hasMaster ? this.data.selectedMasterSubject : this.data.selectedDoctorSubject;
    const subjectList = hasMaster ? this.data.masterSubjects : this.data.doctorSubjects;
    
    console.log('筛选参数：', { filterType, selectedId, subjectListLength: subjectList.length });
    
    const selectedSubject = subjectList.find(s => s.id === selectedId);

    // 检查是否找到专业
    if (!selectedSubject) {
      console.error('未找到选中的专业', {
        filterType,
        selectedId,
        selectedMasterSubject: this.data.selectedMasterSubject,
        selectedDoctorSubject: this.data.selectedDoctorSubject,
        masterSubjects: this.data.masterSubjects,
        doctorSubjects: this.data.doctorSubjects
      });
      wx.showToast({
        title: '专业信息错误，请重新选择',
        icon: 'none'
      });
      return;
    }

    console.log('找到选中的专业：', selectedSubject);

    // 进入筛选模式，但保持当前方向
    this.setData({
      isFilterMode: true,
      filterType: filterType,
      filterSubjectName: selectedSubject.subject_name,
      showFilterPopup: false,
      currentPage: 1,
      professorList: [],
      filteredProfessorsByDept: {} // 清空缓存
    }, () => {
      // 加载当前方向的筛选结果
      this.loadProfessors(false);
    });

    wx.showToast({
      title: `已选择：${selectedSubject.subject_name}`,
      icon: 'success'
    });
  },

  // 新增：重置筛选
  resetFilter() {
    this.setData({
      selectedMasterSubject: null,
      selectedDoctorSubject: null,
      isFilterMode: false,
      filterType: '',
      filterSubjectName: '',
      showFilterPopup: false,
      currentPage: 1,
      professorList: [],
      filteredProfessorsByDept: {} // 清空缓存
    }, () => {
      // 重新加载当前方向的所有导师
      this.loadProfessors(false);
    });

    wx.showToast({
      title: '已清除筛选',
      icon: 'success'
    });
  },

  // 新增：监听禁用标签的点击事件
  onClickDisabled(event) {
    // 只在搜索模式下才显示提示
    if (this.data.isSearchMode) {
      wx.showToast({
        title: '搜索模式下无法切换方向，请先退出搜索',
        icon: 'none',
        duration: 2000
      });
    }
  },

  // 修改 onChange 方法，在切换方向时重新加载数据
  onChange(event) {
    const departmentIndex = event.detail.name;
    const department = this.data.departmentList[departmentIndex];

    // 添加防御性检查
    if (!department || !department.id) {
      console.error('无效的方向数据', departmentIndex, department);
      return;
    }
    
    wx.showToast({
      title: `正在查看 ${event.detail.title}`,
      icon: 'none',
    });

    // 切换方向时重置数据并加载新方向的导师（包括筛选模式）
    this.setData({
      active: departmentIndex,
      selectedDepartmentId: department.id,
      currentPage: 1,
      professorList: []
    }, () => {
      console.log('切换到方向:', department.department_name, 'ID:', department.id);
      this.loadProfessors();
    });
  },
  formatDate: function (dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const seconds = date.getSeconds();

    return `${year}-${this.padZero(month)}-${this.padZero(day)} ${this.padZero(hours)}:${this.padZero(minutes)}:${this.padZero(seconds)}`;
  },
  padZero: function (num) {
    return num < 10 ? '0' + num : num;
  },

  getSelectTime(option) {
    var that = this; // 将当前页面对象保存到变量 that 中
    wx.request({
      url: `${config.BASE_URL}/Select_Information/get-select-time/`,
      method: "GET",
      success: function(res) {
        // console.log(res.data)
        that.setData({
          open_time: that.formatDate(res.data[0]['open_time']),
          close_time: that.formatDate(res.data[0]['close_time'])
        });
        // console.log("professorList", res.data['professors'])
      },
      fail: function(err) {
        console.error('获取导师信息失败：', err);
        // 在这里处理请求失败后的逻辑
      },
      complete: function(res) {
      }
    })

  },


  
  /**
   * 生命周期函数--监听页面加载
   */
  // 修改 onLoad，初始加载时只加载第一页数据
  // 修改 onLoad，初始加载时只加载第一页数据
  onLoad(options) {
    const usertype = wx.getStorageSync('usertype');
    this.setData({
      usertype: usertype,
    });
    this.getSelectTime();

    var that = this;
    
    // 优化方案：一次请求同时获取方向列表和第一个方向的导师
    // 显示加载提示
    wx.showLoading({
      title: '加载中...',
      mask: true
    });
    
    wx.request({
      url: `${config.BASE_URL}/Professor_Student_Manage/professors_and_departments/`,
      method: "GET",
      data: {
        page: 1,
        page_size: that.data.pageSize  // 只加载第一页导师数据
        // 不传 department_id，后端会返回所有方向 + 前N个导师
      },
      success: function(res) {
        wx.hideLoading();
        
        const departments = res.data['departments'];
        const professors = res.data['professors'];
        
        // 如果有导师数据，获取第一个导师所属的方向作为初始方向
        let initialDepartmentId = null;
        let initialActive = 0;
        
        if (professors && professors.length > 0 && departments && departments.length > 0) {
          // 找到第一个导师所属的方向
          const firstProfDeptId = professors[0].department;
          const deptIndex = departments.findIndex(d => d.id === firstProfDeptId);
          if (deptIndex !== -1) {
            initialDepartmentId = firstProfDeptId;
            initialActive = deptIndex;
          } else {
            // 如果找不到，使用第一个方向
            initialDepartmentId = departments[0].id;
            initialActive = 0;
          }
        } else if (departments && departments.length > 0) {
          initialDepartmentId = departments[0].id;
          initialActive = 0;
        }
        
        that.setData({
          departmentList: departments,
          professorList: professors,
          selectedDepartmentId: initialDepartmentId,
          active: initialActive,
          hasNextPage: res.data['has_next'],
          currentPage: res.data['current_page']
        });
        
        // 如果没有导师数据但有方向，则加载第一个方向的导师
        if ((!professors || professors.length === 0) && initialDepartmentId) {
          that.loadProfessors(false);
        }
      },
      fail: function(err) {
        wx.hideLoading();
        console.error('获取方向信息失败：', err);
        wx.showToast({
          title: '加载失败，请重试',
          icon: 'none'
        });
      }
    });
  },

  // 新增：加载导师列表的方法
  loadProfessors(isLoadMore = false) {
    const that = this;
    
    if (this.data.isLoadingMore) {
      return; // 避免重复加载
    }

    this.setData({
      isLoadingMore: true
    });

    const params = {
      page: this.data.currentPage,
      page_size: this.data.pageSize
    };

    // 如果在搜索模式，添加搜索关键词
    if (this.data.isSearchMode && this.data.searchKeyword) {
      params.search = this.data.searchKeyword;
    } else if (this.data.isFilterMode) {
      // 如果在筛选模式，添加专业筛选参数，并且也要传递方向ID
      if (this.data.filterType === 'master' && this.data.selectedMasterSubject !== null) {
        // 确保是数字类型
        const masterId = typeof this.data.selectedMasterSubject === 'number' 
          ? this.data.selectedMasterSubject 
          : parseInt(this.data.selectedMasterSubject);
        params.master_subject_ids = masterId.toString();
      }
      if (this.data.filterType === 'doctor' && this.data.selectedDoctorSubject !== null) {
        // 确保是数字类型
        const doctorId = typeof this.data.selectedDoctorSubject === 'number' 
          ? this.data.selectedDoctorSubject 
          : parseInt(this.data.selectedDoctorSubject);
        params.doctor_subject_ids = doctorId.toString();
      }
      
      // 筛选模式下也要按方向过滤
      const departmentId = this.data.selectedDepartmentId || 
        (this.data.departmentList && this.data.departmentList.length > 0 && this.data.active >= 0
          ? this.data.departmentList[this.data.active].id 
          : null);
      
      if (departmentId) {
        params.department_id = departmentId;
        if (!this.data.selectedDepartmentId) {
          this.setData({
            selectedDepartmentId: departmentId
          });
        }
      }
    } else {
      // 如果不在搜索或筛选模式，确保使用当前选中的方向ID
      // 优先使用 selectedDepartmentId，如果为空则从当前 active 的 tab 获取
      const departmentId = this.data.selectedDepartmentId || 
        (this.data.departmentList && this.data.departmentList.length > 0 && this.data.active >= 0
          ? this.data.departmentList[this.data.active].id 
          : null);
      
      if (departmentId) {
        params.department_id = departmentId;
        // 同步更新 selectedDepartmentId，确保状态一致
        if (!this.data.selectedDepartmentId) {
          this.setData({
            selectedDepartmentId: departmentId
          });
        }
      } else {
        console.error('无法获取当前方向ID，active:', this.data.active, 'departmentList:', this.data.departmentList);
      }
    }

    wx.request({
      url: `${config.BASE_URL}/Professor_Student_Manage/professors_and_departments/`,
      method: "GET",
      data: params,
      success: function(res) {
        const newProfessors = res.data['professors'];
        const updatedList = isLoadMore 
          ? that.data.professorList.concat(newProfessors)
          : newProfessors;

        that.setData({
          professorList: updatedList,
          hasNextPage: res.data['has_next'],
          currentPage: res.data['current_page'],
          isLoadingMore: false,
          searchResultCount: res.data['total_count']
        });

        // 如果是搜索模式且有结果，自动切换到对应的tab
        if (that.data.isSearchMode && newProfessors.length > 0 && !isLoadMore) {
          const firstProfessor = newProfessors[0];
          const departmentIndex = that.data.departmentList.findIndex(
            dept => dept.id === firstProfessor.department
          );
          if (departmentIndex !== -1) {
            that.setData({
              active: departmentIndex
            });
          }
        }

        // 如果是首次加载，也加载方向列表
        if (!isLoadMore && res.data['departments']) {
          that.setData({
            departmentList: res.data['departments']
          });
        }

        // 搜索结果提示
        if (that.data.isSearchMode && !isLoadMore) {
          if (newProfessors.length === 0) {
            wx.showToast({
              title: '未找到匹配的导师',
              icon: 'none'
            });
          } else {
            wx.showToast({
              title: `找到 ${res.data['total_count']} 位导师`,
              icon: 'success'
            });
          }
        }

        // 筛选结果提示 - 不显示弹框，只在页面显示
        // if (that.data.isFilterMode && !isLoadMore) {
        //   if (newProfessors.length === 0) {
        //     wx.showToast({
        //       title: '该方向下没有符合条件的导师',
        //       icon: 'none'
        //     });
        //   }
        // }
      },
      fail: function(err) {
        console.error('获取导师信息失败：', err);
        that.setData({
          isLoadingMore: false,
          professorList: that.data.professorList || [] // 确保不是 undefined
        });
        wx.showToast({
          title: '加载失败，请重试',
          icon: 'none'
        });
      }
    });
  },

  // 新增：上拉加载更多
  loadMoreProfessors() {
    if (!this.data.hasNextPage || this.data.isLoadingMore) {
      return;
    }

    // 添加调试日志，检查状态
    console.log('触发加载更多，当前页:', this.data.currentPage, 
                '方向ID:', this.data.selectedDepartmentId, 
                'active:', this.data.active);

    this.setData({
      currentPage: this.data.currentPage + 1
    }, () => {
      this.loadProfessors(true);
    });
  },

  // 修改下拉刷新方法
  onPullDownRefresh() {
    this.setData({
      isTriggered: true,
      refreshText: "刷新导师信息中...",
      currentPage: 1
    });
    
    // 如果在搜索模式，重新搜索；否则刷新当前方向
    this.loadProfessors(false);
    
    setTimeout(() => {
      this.setData({
        isTriggered: false,
        refreshText: "下拉刷新"
      });
    }, 1000);
  },
  

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    // 初始化 tabBar
    this.getTabBar().init();
    
    // 更新全局状态
    const app = getApp();
    this.setData({
      isPopupOpen: app.globalData.isPopupOpen
    });
    
    // 检查数据是否需要刷新
    // 如果导师列表为空，或者没有选中的方向ID，则重新加载
    if (!this.data.professorList || this.data.professorList.length === 0) {
      console.log('导师列表为空，重新加载数据');
      // 如果还没有方向列表，则完全重新加载
      if (!this.data.departmentList || this.data.departmentList.length === 0) {
        this.onLoad();
      } else if (this.data.selectedDepartmentId) {
        // 如果有方向ID，直接加载该方向的导师
        this.setData({
          currentPage: 1
        }, () => {
          this.loadProfessors(false);
        });
      } else {
        // 如果没有选中方向，加载第一个方向
        const firstDepartmentId = this.data.departmentList[0]?.id;
        if (firstDepartmentId) {
          this.setData({
            selectedDepartmentId: firstDepartmentId,
            active: 0,
            currentPage: 1
          }, () => {
            this.loadProfessors(false);
          });
        } else {
          this.onLoad();
        }
      }
    } else {
      console.log('导师列表存在，无需重新加载');
    }
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
 

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    this.loadMoreProfessors();
  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})