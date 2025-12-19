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
  // 修改 onChange 方法，在切换方向时重新加载数据
  onChange(event) {
    const departmentIndex = event.detail.name;
    const department = this.data.departmentList[departmentIndex];
    
    wx.showToast({
      title: `正在查看 ${event.detail.title}`,
      icon: 'none',
    });

    // 切换方向时重置数据并加载新方向的导师
    this.setData({
      active: departmentIndex,
      selectedDepartmentId: department.id,
      currentPage: 1,
      professorList: []
    }, () => {
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
  onLoad(options) {
    const usertype = wx.getStorageSync('usertype');
    this.setData({
      usertype: usertype,
    });
    this.getSelectTime();

    var that = this;
    
    // 方案1：先加载所有方向，然后加载第一个方向的导师（推荐）
    wx.request({
      url: `${config.BASE_URL}/Professor_Student_Manage/professors_and_departments/`,
      method: "GET",
      data: {
        page: 1,
        page_size: 999 // 加载所有方向
      },
      success: function(res) {
        const departments = res.data['departments'];
        const firstDepartmentId = departments && departments.length > 0 ? departments[0].id : null;
        
        that.setData({
          departmentList: departments,
          selectedDepartmentId: firstDepartmentId
        });
        
        // 加载第一个方向的导师
        if (firstDepartmentId) {
          that.loadProfessors(false);
        }
      },
      fail: function(err) {
        console.error('获取方向信息失败：', err);
      }
    });
    
    /* 方案2：一次性加载所有数据（如果导师不多可以用这个）
    wx.request({
      url: `${config.BASE_URL}/Professor_Student_Manage/professors_and_departments/`,
      method: "GET",
      data: {
        page: 1,
        page_size: that.data.pageSize
      },
      success: function(res) {
        const departments = res.data['departments'];
        const firstDepartmentId = departments && departments.length > 0 ? departments[0].id : null;
        
        that.setData({
          departmentList: departments,
          professorList: res.data['professors'],
          hasNextPage: res.data['has_next'],
          currentPage: res.data['current_page'],
          selectedDepartmentId: firstDepartmentId
        });
      },
      fail: function(err) {
        console.error('获取导师信息失败：', err);
      }
    });
    */
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

    // 如果选中了特定方向，添加方向过滤
    if (this.data.selectedDepartmentId) {
      params.department_id = this.data.selectedDepartmentId;
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
          isLoadingMore: false
        });

        // 如果是首次加载，也加载方向列表
        if (!isLoadMore && res.data['departments']) {
          that.setData({
            departmentList: res.data['departments']
          });
        }
      },
      fail: function(err) {
        console.error('获取导师信息失败：', err);
        that.setData({
          isLoadingMore: false
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
    this.onLoad()
    this.getTabBar().init()
    const app = getApp();
    this.setData({
      isPopupOpen: app.globalData.isPopupOpen
    })
    // console.log("app.globalData.isPopupOpen", app.globalData.isPopupOpen)
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