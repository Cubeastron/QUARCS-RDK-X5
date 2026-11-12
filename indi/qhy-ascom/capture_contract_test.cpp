#include "qhy_ccd.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

// These definitions replace SDK entry points only in the test executable.
// Discovery is disabled, so this test never opens real USB hardware.
static unsigned exposureWrites = 0, roiWrites = 0, initCalls = 0;
static uint32_t exposureResult = QHYCCD_SUCCESS, roiResult = QHYCCD_SUCCESS;
static uint32_t triggerResult = QHYCCD_READ_DIRECTLY, initResult = QHYCCD_SUCCESS;
static double writtenExposure = 0;
extern "C" {
uint32_t InitQHYCCDResource() { return QHYCCD_SUCCESS; }
uint32_t ReleaseQHYCCDResource() { return QHYCCD_SUCCESS; }
uint32_t ScanQHYCCD() { return 0; }
uint32_t InitQHYCCD(qhyccd_handle *) { ++initCalls; return initResult; }
uint32_t SetQHYCCDParam(qhyccd_handle *, CONTROL_ID control, double value)
{
    if (control == CONTROL_EXPOSURE)
    {
        ++exposureWrites;
        writtenExposure = value;
        return exposureResult;
    }
    return QHYCCD_SUCCESS;
}
uint32_t SetQHYCCDBinMode(qhyccd_handle *, uint32_t, uint32_t) { return QHYCCD_SUCCESS; }
uint32_t SetQHYCCDResolution(qhyccd_handle *, uint32_t, uint32_t, uint32_t, uint32_t)
{
    ++roiWrites;
    return roiResult;
}
uint32_t SetQHYCCDBitsMode(qhyccd_handle *, uint32_t) { return QHYCCD_SUCCESS; }
uint32_t ExpQHYCCDSingleFrame(qhyccd_handle *) { return triggerResult; }
}

static void require(bool condition, const char *message)
{
    if (!condition) throw std::runtime_error(message);
}

class QHYCaptureTest : public QHYCCD
{
public:
    QHYCaptureTest(const char *model = "QHY5PII-C") : QHYCCD(model, model)
    {
        initProperties();
        SetCCDCapability(0);
        SetCCDParams(16, 12, 16, 2.2, 2.2);
        PrimaryCCD.setFrame(0, 0, 16, 12);
        PrimaryCCD.setBin(1, 1);
        IgnoreOverscanArea = false;
        m_CameraHandle = reinterpret_cast<qhyccd_handle *>(0x1234);
        m_ThreadRequest = StateIdle;
        m_ThreadState = StateIdle;
    }

    void run()
    {
        require(std::string(getDeviceName()) == "QHY CCD QHY5PII-C", "camera model name changed");
        require(StartExposure(1.0f), "first exposure failed");
        require(exposureWrites == 1 && writtenExposure == 1000000, "first exposure was not written");
        require(roiWrites == 1 && m_CaptureROIValid, "first ROI was not written");
        require(m_SingleFrameReadDelay == 0, "READ_DIRECTLY still waits");
        require(StartExposure(1.0f), "repeat exposure failed");
        require(exposureWrites == 1 && roiWrites == 1, "unchanged exposure or ROI rewritten");
        require(StartExposure(2.0f), "changed exposure failed");
        require(exposureWrites == 2 && writtenExposure == 2000000, "changed exposure not written");
        require(roiWrites == 1, "exposure change unnecessarily rewrote ROI");

        exposureResult = QHYCCD_ERROR;
        require(!StartExposure(3.0f), "SDK parameter error ignored");
        require(m_LastExposureRequestuS == -1, "failed write retained valid cache");
        exposureResult = QHYCCD_SUCCESS;
        require(StartExposure(3.0f), "failed parameter was not retried");
        require(exposureWrites == 4 && writtenExposure == 3000000, "failed parameter retry count wrong");

        PrimaryCCD.setFrame(1, 0, 14, 12);
        require(StartExposure(3.0f), "changed ROI failed");
        require(roiWrites == 2, "changed ROI was skipped");
        PrimaryCCD.setFrame(2, 0, 12, 12);
        roiResult = QHYCCD_ERROR;
        require(!StartExposure(3.0f), "SDK ROI failure ignored");
        require(!m_CaptureROIValid && m_LastExposureRequestuS == -1, "failed ROI retained caches");
        roiResult = QHYCCD_SUCCESS;
        require(StartExposure(3.0f), "failed ROI not retried");
        require(roiWrites == 4, "failed ROI retry count wrong");

        unsigned before = exposureWrites;
        require(initializeCamera() == QHYCCD_SUCCESS, "init failed");
        require(StartExposure(3.0f), "capture after reinit failed");
        require(exposureWrites == before + 1 && roiWrites == 5, "reinit reused old settings");
        initResult = QHYCCD_ERROR;
        require(initializeCamera() == QHYCCD_ERROR, "init failure ignored");
        require(m_LastExposureRequestuS == -1 && !m_CaptureROIValid, "failed init retained caches");
        initResult = QHYCCD_SUCCESS;

        triggerResult = QHYCCD_SUCCESS;
        require(StartExposure(10.0f), "long exposure failed");
        require(m_SingleFrameReadDelay == 7.0, "long exposure does not leave last 3s to SDK");
        require(StartExposure(1.0f), "short exposure failed");
        require(m_SingleFrameReadDelay == 0, "short exposure has extra wait");
        triggerResult = QHYCCD_READ_DIRECTLY;
        require(StartExposure(10.0f), "direct long exposure failed");
        require(m_SingleFrameReadDelay == 0, "direct long exposure has extra wait");
        triggerResult = QHYCCD_ERROR;
        require(!StartExposure(10.0f), "trigger error ignored");
        require(m_LastExposureRequestuS == -1 && !m_CaptureROIValid, "trigger failure retained caches");
        triggerResult = QHYCCD_READ_DIRECTLY;
        require(StartExposure(10.0f), "trigger retry failed");
        std::cout << "PASS: first/repeated/changed exposure; SDK failure/retry; ROI change/failure/retry; "
                  << "successful/failed reinit; READ_DIRECTLY; short/long exposure; trigger failure/retry\n";
    }

    void checkOtherModel()
    {
        unsigned before = roiWrites;
        require(StartExposure(1.0f) && StartExposure(1.0f), "other-model exposure failed");
        require(m_SingleFrameReadDelay == 1.0 && roiWrites == before + 2, "other-model readout behavior changed");
        std::cout << "PASS: other-model countdown and ROI behavior preserved\n";
    }
};

int main()
{
    try
    {
        QHYCaptureTest camera;
        camera.run();
        QHYCaptureTest other("QHYTEST");
        other.checkOtherModel();
        std::cout << "All capture contract checks passed; no hardware used.\n";
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
