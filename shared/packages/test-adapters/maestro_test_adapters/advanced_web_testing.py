#!/usr/bin/env python3
"""
Advanced Web Testing with Complex User Journeys

This module provides comprehensive web testing capabilities with:
- Complex multi-step user journeys
- Real-world interaction patterns
- Performance monitoring
- Accessibility testing
- Visual regression testing
"""

import asyncio
import json
import time
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import os
import base64

logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import Select
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available - web testing features will be limited")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - advanced web testing features will be limited")


class ActionType(Enum):
    """Types of user actions"""
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    HOVER = "hover"
    DRAG_DROP = "drag_drop"
    SCROLL = "scroll"
    WAIT = "wait"
    NAVIGATE = "navigate"
    SCREENSHOT = "screenshot"
    ASSERT = "assert"
    EXTRACT = "extract"
    UPLOAD_FILE = "upload_file"
    JAVASCRIPT = "javascript"


class AssertionType(Enum):
    """Types of assertions"""
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_TEXT = "element_text"
    ELEMENT_ATTRIBUTE = "element_attribute"
    PAGE_TITLE = "page_title"
    PAGE_URL = "page_url"
    ELEMENT_COUNT = "element_count"
    ELEMENT_NOT_EXISTS = "element_not_exists"
    PERFORMANCE = "performance"


@dataclass
class UserAction:
    """Individual user action in a journey"""
    action_type: ActionType
    selector: Optional[str] = None
    value: Optional[str] = None
    timeout: float = 10.0
    description: str = ""
    wait_after: float = 0.0
    optional: bool = False  # If true, continue on failure
    retry_count: int = 3
    metadata: Dict[str, Any] = None


@dataclass
class UserAssertion:
    """Assertion to validate during journey"""
    assertion_type: AssertionType
    selector: Optional[str] = None
    expected_value: Any = None
    timeout: float = 10.0
    description: str = ""
    tolerance: Optional[float] = None  # For performance assertions


@dataclass
class UserJourney:
    """Complete user journey definition"""
    name: str
    description: str
    steps: List[UserAction]
    assertions: List[UserAssertion]
    setup_actions: List[UserAction] = None
    teardown_actions: List[UserAction] = None
    variables: Dict[str, Any] = None
    tags: List[str] = None
    critical: bool = False
    expected_duration: float = 30.0


@dataclass
class JourneyResult:
    """Result of a user journey execution"""
    journey_name: str
    status: str  # passed, failed, error
    duration: float
    steps_executed: int
    steps_passed: int
    steps_failed: int
    assertions_passed: int
    assertions_failed: int
    error_message: Optional[str] = None
    step_results: List[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any] = None
    screenshots: List[str] = None
    network_logs: List[Dict[str, Any]] = None


class AdvancedSeleniumAdapter:
    """
    Advanced Selenium Adapter with Complex User Journeys

    Features:
    - Multi-step user scenarios
    - Performance monitoring
    - Screenshot capture
    - Network interception
    - Accessibility testing
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.driver = None
        self.wait = None
        self.screenshots_dir = None

    async def initialize(self) -> bool:
        """Initialize Selenium with advanced capabilities"""
        if not SELENIUM_AVAILABLE:
            return False

        try:
            # Setup Chrome options
            chrome_options = ChromeOptions()

            # Headless configuration
            if self.config.get("headless", True):
                chrome_options.add_argument("--headless")

            # Performance and reliability options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # Enable performance logging
            chrome_options.add_argument("--enable-logging")
            chrome_options.add_argument("--log-level=0")

            # Set capabilities for performance monitoring
            capabilities = chrome_options.to_capabilities()
            capabilities['goog:loggingPrefs'] = {
                'browser': 'ALL',
                'driver': 'ALL',
                'performance': 'ALL'
            }

            # Enable network logging
            chrome_options.add_argument("--enable-network-service-logging")

            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)

            # Setup screenshots directory
            self.screenshots_dir = self.config.get("screenshots_dir", "/tmp/selenium_screenshots")
            os.makedirs(self.screenshots_dir, exist_ok=True)

            logger.info("Advanced Selenium adapter initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            return False

    async def execute_user_journey(self, journey: UserJourney) -> JourneyResult:
        """Execute a complex user journey"""
        start_time = time.time()

        result = JourneyResult(
            journey_name=journey.name,
            status="passed",
            duration=0.0,
            steps_executed=0,
            steps_passed=0,
            steps_failed=0,
            assertions_passed=0,
            assertions_failed=0,
            step_results=[],
            performance_metrics={},
            screenshots=[],
            network_logs=[]
        )

        try:
            # Setup actions
            if journey.setup_actions:
                await self._execute_action_sequence(journey.setup_actions, result, "setup")

            # Main journey steps
            await self._execute_action_sequence(journey.steps, result, "main")

            # Validate assertions
            await self._validate_assertions(journey.assertions, result)

            # Teardown actions
            if journey.teardown_actions:
                await self._execute_action_sequence(journey.teardown_actions, result, "teardown")

            # Collect performance metrics
            result.performance_metrics = await self._collect_performance_metrics()

            # Determine final status
            if result.steps_failed > 0 or result.assertions_failed > 0:
                result.status = "failed"

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logger.error(f"Journey execution failed: {e}")

        finally:
            result.duration = time.time() - start_time

        return result

    async def _execute_action_sequence(self, actions: List[UserAction], result: JourneyResult, phase: str):
        """Execute a sequence of user actions"""

        for i, action in enumerate(actions):
            step_start = time.time()
            step_result = {
                "phase": phase,
                "step_index": i,
                "action": action.action_type.value,
                "description": action.description,
                "status": "pending",
                "duration": 0.0,
                "error": None
            }

            try:
                result.steps_executed += 1

                # Execute the action
                await self._execute_single_action(action)

                # Wait after action if specified
                if action.wait_after > 0:
                    await asyncio.sleep(action.wait_after)

                step_result["status"] = "passed"
                result.steps_passed += 1

            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)

                if action.optional:
                    logger.warning(f"Optional step failed: {e}")
                else:
                    result.steps_failed += 1
                    if not action.optional:
                        raise

            finally:
                step_result["duration"] = time.time() - step_start
                result.step_results.append(step_result)

    async def _execute_single_action(self, action: UserAction):
        """Execute a single user action"""

        if action.action_type == ActionType.NAVIGATE:
            self.driver.get(action.value)

        elif action.action_type == ActionType.CLICK:
            element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, action.selector)))
            element.click()

        elif action.action_type == ActionType.TYPE:
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, action.selector)))
            element.clear()
            element.send_keys(action.value)

        elif action.action_type == ActionType.SELECT:
            element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, action.selector)))
            select = Select(element)
            select.select_by_visible_text(action.value)

        elif action.action_type == ActionType.HOVER:
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, action.selector)))
            ActionChains(self.driver).move_to_element(element).perform()

        elif action.action_type == ActionType.DRAG_DROP:
            metadata = action.metadata or {}
            source = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, action.selector)))
            target = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, metadata.get("target_selector"))))
            ActionChains(self.driver).drag_and_drop(source, target).perform()

        elif action.action_type == ActionType.SCROLL:
            if action.selector:
                element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, action.selector)))
                self.driver.execute_script("arguments[0].scrollIntoView();", element)
            else:
                # Scroll by pixel amount
                pixels = int(action.value) if action.value else 500
                self.driver.execute_script(f"window.scrollBy(0, {pixels});")

        elif action.action_type == ActionType.WAIT:
            await asyncio.sleep(float(action.value))

        elif action.action_type == ActionType.SCREENSHOT:
            screenshot_path = os.path.join(self.screenshots_dir, f"screenshot_{uuid.uuid4().hex[:8]}.png")
            self.driver.save_screenshot(screenshot_path)

        elif action.action_type == ActionType.UPLOAD_FILE:
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, action.selector)))
            element.send_keys(action.value)

        elif action.action_type == ActionType.JAVASCRIPT:
            self.driver.execute_script(action.value)

        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

    async def _validate_assertions(self, assertions: List[UserAssertion], result: JourneyResult):
        """Validate all assertions"""

        for assertion in assertions:
            try:
                await self._validate_single_assertion(assertion)
                result.assertions_passed += 1
            except Exception as e:
                result.assertions_failed += 1
                logger.error(f"Assertion failed: {assertion.description} - {e}")

    async def _validate_single_assertion(self, assertion: UserAssertion):
        """Validate a single assertion"""

        if assertion.assertion_type == AssertionType.ELEMENT_VISIBLE:
            element = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, assertion.selector)))

        elif assertion.assertion_type == AssertionType.ELEMENT_TEXT:
            element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, assertion.selector)))
            actual_text = element.text
            if actual_text != assertion.expected_value:
                raise AssertionError(f"Expected text '{assertion.expected_value}', got '{actual_text}'")

        elif assertion.assertion_type == AssertionType.PAGE_TITLE:
            actual_title = self.driver.title
            if actual_title != assertion.expected_value:
                raise AssertionError(f"Expected title '{assertion.expected_value}', got '{actual_title}'")

        elif assertion.assertion_type == AssertionType.PAGE_URL:
            actual_url = self.driver.current_url
            if assertion.expected_value not in actual_url:
                raise AssertionError(f"Expected URL to contain '{assertion.expected_value}', got '{actual_url}'")

        elif assertion.assertion_type == AssertionType.ELEMENT_COUNT:
            elements = self.driver.find_elements(By.CSS_SELECTOR, assertion.selector)
            actual_count = len(elements)
            if actual_count != assertion.expected_value:
                raise AssertionError(f"Expected {assertion.expected_value} elements, found {actual_count}")

        elif assertion.assertion_type == AssertionType.ELEMENT_NOT_EXISTS:
            elements = self.driver.find_elements(By.CSS_SELECTOR, assertion.selector)
            if elements:
                raise AssertionError(f"Expected element '{assertion.selector}' not to exist, but found {len(elements)}")

        else:
            raise ValueError(f"Unknown assertion type: {assertion.assertion_type}")

    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics from browser"""
        try:
            # Get performance timing
            performance_timing = self.driver.execute_script("""
                var timing = window.performance.timing;
                return {
                    'navigationStart': timing.navigationStart,
                    'domContentLoadedEventEnd': timing.domContentLoadedEventEnd,
                    'loadEventEnd': timing.loadEventEnd,
                    'responseStart': timing.responseStart,
                    'responseEnd': timing.responseEnd
                };
            """)

            # Calculate metrics
            navigation_start = performance_timing['navigationStart']
            metrics = {
                'page_load_time': performance_timing['loadEventEnd'] - navigation_start,
                'dom_content_loaded': performance_timing['domContentLoadedEventEnd'] - navigation_start,
                'response_time': performance_timing['responseEnd'] - performance_timing['responseStart'],
                'first_paint': 0,  # Would need Performance API
                'largest_contentful_paint': 0  # Would need Performance API
            }

            return metrics

        except Exception as e:
            logger.warning(f"Failed to collect performance metrics: {e}")
            return {}

    async def cleanup(self) -> bool:
        """Cleanup Selenium resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error during driver cleanup: {e}")

        return True


class AdvancedPlaywrightAdapter:
    """
    Advanced Playwright Adapter with Complex User Journeys

    Features:
    - Advanced browser automation
    - Network interception
    - Performance monitoring
    - Mobile device emulation
    - Accessibility testing
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.screenshots_dir = None

    async def initialize(self) -> bool:
        """Initialize Playwright with advanced capabilities"""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        try:
            self.playwright = await async_playwright().start()

            # Browser configuration
            browser_type = self.config.get("browser", "chromium")  # chromium, firefox, webkit
            headless = self.config.get("headless", True)

            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(headless=headless)
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=headless)
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(headless=headless)

            # Context configuration
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": self.config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
                "locale": self.config.get("locale", "en-US"),
                "timezone_id": self.config.get("timezone", "America/New_York"),
                "permissions": ["geolocation"] if self.config.get("enable_geolocation") else []
            }

            # Mobile device emulation
            device = self.config.get("device")
            if device:
                device_config = self.playwright.devices.get(device)
                if device_config:
                    context_options.update(device_config)

            self.context = await self.browser.new_context(**context_options)

            # Enable request/response logging
            await self.context.route("**/*", self._log_network_request)

            # Create page
            self.page = await self.context.new_page()

            # Setup console logging
            self.page.on("console", self._log_console_message)
            self.page.on("pageerror", self._log_page_error)

            # Setup screenshots directory
            self.screenshots_dir = self.config.get("screenshots_dir", "/tmp/playwright_screenshots")
            os.makedirs(self.screenshots_dir, exist_ok=True)

            logger.info("Advanced Playwright adapter initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False

    async def execute_user_journey(self, journey: UserJourney) -> JourneyResult:
        """Execute a complex user journey with Playwright"""
        start_time = time.time()

        result = JourneyResult(
            journey_name=journey.name,
            status="passed",
            duration=0.0,
            steps_executed=0,
            steps_passed=0,
            steps_failed=0,
            assertions_passed=0,
            assertions_failed=0,
            step_results=[],
            performance_metrics={},
            screenshots=[],
            network_logs=[]
        )

        try:
            # Setup actions
            if journey.setup_actions:
                await self._execute_action_sequence(journey.setup_actions, result, "setup")

            # Main journey steps
            await self._execute_action_sequence(journey.steps, result, "main")

            # Validate assertions
            await self._validate_assertions(journey.assertions, result)

            # Teardown actions
            if journey.teardown_actions:
                await self._execute_action_sequence(journey.teardown_actions, result, "teardown")

            # Collect performance metrics
            result.performance_metrics = await self._collect_performance_metrics()

            # Determine final status
            if result.steps_failed > 0 or result.assertions_failed > 0:
                result.status = "failed"

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logger.error(f"Journey execution failed: {e}")

        finally:
            result.duration = time.time() - start_time

        return result

    async def _execute_action_sequence(self, actions: List[UserAction], result: JourneyResult, phase: str):
        """Execute a sequence of user actions with Playwright"""

        for i, action in enumerate(actions):
            step_start = time.time()
            step_result = {
                "phase": phase,
                "step_index": i,
                "action": action.action_type.value,
                "description": action.description,
                "status": "pending",
                "duration": 0.0,
                "error": None
            }

            try:
                result.steps_executed += 1

                # Execute the action
                await self._execute_single_action(action)

                # Wait after action if specified
                if action.wait_after > 0:
                    await asyncio.sleep(action.wait_after)

                step_result["status"] = "passed"
                result.steps_passed += 1

            except Exception as e:
                step_result["status"] = "failed"
                step_result["error"] = str(e)

                if action.optional:
                    logger.warning(f"Optional step failed: {e}")
                else:
                    result.steps_failed += 1
                    if not action.optional:
                        raise

            finally:
                step_result["duration"] = time.time() - step_start
                result.step_results.append(step_result)

    async def _execute_single_action(self, action: UserAction):
        """Execute a single user action with Playwright"""

        if action.action_type == ActionType.NAVIGATE:
            await self.page.goto(action.value, timeout=action.timeout * 1000)

        elif action.action_type == ActionType.CLICK:
            await self.page.click(action.selector, timeout=action.timeout * 1000)

        elif action.action_type == ActionType.TYPE:
            await self.page.fill(action.selector, action.value, timeout=action.timeout * 1000)

        elif action.action_type == ActionType.SELECT:
            await self.page.select_option(action.selector, action.value, timeout=action.timeout * 1000)

        elif action.action_type == ActionType.HOVER:
            await self.page.hover(action.selector, timeout=action.timeout * 1000)

        elif action.action_type == ActionType.DRAG_DROP:
            metadata = action.metadata or {}
            source_selector = action.selector
            target_selector = metadata.get("target_selector")

            source = await self.page.query_selector(source_selector)
            target = await self.page.query_selector(target_selector)

            if source and target:
                source_box = await source.bounding_box()
                target_box = await target.bounding_box()

                await self.page.mouse.move(
                    source_box["x"] + source_box["width"] / 2,
                    source_box["y"] + source_box["height"] / 2
                )
                await self.page.mouse.down()
                await self.page.mouse.move(
                    target_box["x"] + target_box["width"] / 2,
                    target_box["y"] + target_box["height"] / 2
                )
                await self.page.mouse.up()

        elif action.action_type == ActionType.SCROLL:
            if action.selector:
                await self.page.evaluate(f'document.querySelector("{action.selector}").scrollIntoView()')
            else:
                pixels = int(action.value) if action.value else 500
                await self.page.evaluate(f"window.scrollBy(0, {pixels})")

        elif action.action_type == ActionType.WAIT:
            await asyncio.sleep(float(action.value))

        elif action.action_type == ActionType.SCREENSHOT:
            screenshot_path = os.path.join(self.screenshots_dir, f"screenshot_{uuid.uuid4().hex[:8]}.png")
            await self.page.screenshot(path=screenshot_path, full_page=True)

        elif action.action_type == ActionType.UPLOAD_FILE:
            await self.page.set_input_files(action.selector, action.value)

        elif action.action_type == ActionType.JAVASCRIPT:
            await self.page.evaluate(action.value)

        else:
            raise ValueError(f"Unknown action type: {action.action_type}")

    async def _validate_assertions(self, assertions: List[UserAssertion], result: JourneyResult):
        """Validate all assertions with Playwright"""

        for assertion in assertions:
            try:
                await self._validate_single_assertion(assertion)
                result.assertions_passed += 1
            except Exception as e:
                result.assertions_failed += 1
                logger.error(f"Assertion failed: {assertion.description} - {e}")

    async def _validate_single_assertion(self, assertion: UserAssertion):
        """Validate a single assertion with Playwright"""

        timeout = assertion.timeout * 1000  # Convert to milliseconds

        if assertion.assertion_type == AssertionType.ELEMENT_VISIBLE:
            await self.page.wait_for_selector(assertion.selector, state="visible", timeout=timeout)

        elif assertion.assertion_type == AssertionType.ELEMENT_TEXT:
            element = await self.page.wait_for_selector(assertion.selector, timeout=timeout)
            actual_text = await element.text_content()
            if actual_text != assertion.expected_value:
                raise AssertionError(f"Expected text '{assertion.expected_value}', got '{actual_text}'")

        elif assertion.assertion_type == AssertionType.PAGE_TITLE:
            actual_title = await self.page.title()
            if actual_title != assertion.expected_value:
                raise AssertionError(f"Expected title '{assertion.expected_value}', got '{actual_title}'")

        elif assertion.assertion_type == AssertionType.PAGE_URL:
            actual_url = self.page.url
            if assertion.expected_value not in actual_url:
                raise AssertionError(f"Expected URL to contain '{assertion.expected_value}', got '{actual_url}'")

        elif assertion.assertion_type == AssertionType.ELEMENT_COUNT:
            elements = await self.page.query_selector_all(assertion.selector)
            actual_count = len(elements)
            if actual_count != assertion.expected_value:
                raise AssertionError(f"Expected {assertion.expected_value} elements, found {actual_count}")

        elif assertion.assertion_type == AssertionType.ELEMENT_NOT_EXISTS:
            element = await self.page.query_selector(assertion.selector)
            if element:
                raise AssertionError(f"Expected element '{assertion.selector}' not to exist, but found it")

        elif assertion.assertion_type == AssertionType.PERFORMANCE:
            # Performance assertions (e.g., page load time)
            metrics = await self._collect_performance_metrics()
            metric_name = assertion.selector  # Use selector as metric name
            actual_value = metrics.get(metric_name, 0)

            if actual_value > assertion.expected_value:
                tolerance = assertion.tolerance or 0
                if actual_value > assertion.expected_value + tolerance:
                    raise AssertionError(f"Performance metric '{metric_name}' {actual_value} exceeds threshold {assertion.expected_value}")

        else:
            raise ValueError(f"Unknown assertion type: {assertion.assertion_type}")

    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive performance metrics"""
        try:
            # Get performance timing data
            performance_data = await self.page.evaluate("""
                () => {
                    const timing = performance.timing;
                    const navigation = performance.getEntriesByType('navigation')[0];
                    const paint = performance.getEntriesByType('paint');

                    let metrics = {
                        // Basic timing
                        pageLoadTime: timing.loadEventEnd - timing.navigationStart,
                        domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                        responseTime: timing.responseEnd - timing.responseStart,

                        // Navigation timing
                        dnsLookup: timing.domainLookupEnd - timing.domainLookupStart,
                        tcpConnect: timing.connectEnd - timing.connectStart,
                        serverResponse: timing.responseStart - timing.requestStart,
                        domProcessing: timing.domContentLoadedEventStart - timing.responseEnd,

                        // Memory usage (if available)
                        jsHeapSizeUsed: 0,
                        jsHeapSizeTotal: 0
                    };

                    // Add paint metrics
                    paint.forEach(entry => {
                        if (entry.name === 'first-paint') {
                            metrics.firstPaint = entry.startTime;
                        } else if (entry.name === 'first-contentful-paint') {
                            metrics.firstContentfulPaint = entry.startTime;
                        }
                    });

                    // Add memory info if available
                    if (performance.memory) {
                        metrics.jsHeapSizeUsed = performance.memory.usedJSHeapSize;
                        metrics.jsHeapSizeTotal = performance.memory.totalJSHeapSize;
                    }

                    // Add navigation timing v2 metrics if available
                    if (navigation) {
                        metrics.redirectTime = navigation.redirectEnd - navigation.redirectStart;
                        metrics.workerTime = navigation.workerStart ? navigation.responseStart - navigation.workerStart : 0;
                    }

                    return metrics;
                }
            """)

            return performance_data

        except Exception as e:
            logger.warning(f"Failed to collect performance metrics: {e}")
            return {}

    async def _log_network_request(self, route):
        """Log network requests for analysis"""
        request = route.request
        # Continue with the request
        await route.continue_()

        # Log request details (simplified)
        logger.debug(f"Network request: {request.method} {request.url}")

    def _log_console_message(self, msg):
        """Log console messages from the page"""
        logger.debug(f"Console {msg.type}: {msg.text}")

    def _log_page_error(self, error):
        """Log page errors"""
        logger.error(f"Page error: {error}")

    async def run_accessibility_audit(self) -> Dict[str, Any]:
        """Run accessibility audit using axe-core"""
        try:
            # Inject axe-core library
            await self.page.add_script_tag(url="https://unpkg.com/axe-core@4.4.1/axe.min.js")

            # Run accessibility audit
            audit_results = await self.page.evaluate("""
                async () => {
                    const results = await axe.run();
                    return {
                        violations: results.violations.map(v => ({
                            id: v.id,
                            impact: v.impact,
                            description: v.description,
                            help: v.help,
                            helpUrl: v.helpUrl,
                            nodes: v.nodes.length
                        })),
                        passes: results.passes.length,
                        incomplete: results.incomplete.length,
                        inapplicable: results.inapplicable.length
                    };
                }
            """)

            return audit_results

        except Exception as e:
            logger.error(f"Accessibility audit failed: {e}")
            return {"error": str(e)}

    async def cleanup(self) -> bool:
        """Cleanup Playwright resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            return True

        except Exception as e:
            logger.warning(f"Error during Playwright cleanup: {e}")
            return False


# Predefined user journeys for common scenarios
class UserJourneyTemplates:
    """Common user journey templates"""

    @staticmethod
    def create_login_journey(base_url: str, username: str, password: str) -> UserJourney:
        """Create a standard login user journey"""
        return UserJourney(
            name="User Login Flow",
            description="Standard user authentication journey",
            steps=[
                UserAction(ActionType.NAVIGATE, value=f"{base_url}/login", description="Navigate to login page"),
                UserAction(ActionType.TYPE, selector="input[name='username']", value=username, description="Enter username"),
                UserAction(ActionType.TYPE, selector="input[name='password']", value=password, description="Enter password"),
                UserAction(ActionType.CLICK, selector="button[type='submit']", description="Click login button"),
                UserAction(ActionType.WAIT, value="2", description="Wait for redirect")
            ],
            assertions=[
                UserAssertion(AssertionType.PAGE_URL, expected_value="/dashboard", description="Verify redirect to dashboard"),
                UserAssertion(AssertionType.ELEMENT_VISIBLE, selector=".user-menu", description="Verify user menu visible")
            ],
            critical=True,
            expected_duration=10.0
        )

    @staticmethod
    def create_shopping_cart_journey(base_url: str) -> UserJourney:
        """Create an e-commerce shopping cart journey"""
        return UserJourney(
            name="Shopping Cart Flow",
            description="Add items to cart and proceed to checkout",
            steps=[
                UserAction(ActionType.NAVIGATE, value=f"{base_url}/products", description="Navigate to products"),
                UserAction(ActionType.CLICK, selector=".product-item:first-child .add-to-cart", description="Add first product"),
                UserAction(ActionType.WAIT, value="1", description="Wait for cart update"),
                UserAction(ActionType.CLICK, selector=".product-item:nth-child(2) .add-to-cart", description="Add second product"),
                UserAction(ActionType.CLICK, selector=".cart-icon", description="Open cart"),
                UserAction(ActionType.ASSERT, selector=".cart-items .item", description="Verify cart items"),
                UserAction(ActionType.CLICK, selector=".proceed-checkout", description="Proceed to checkout")
            ],
            assertions=[
                UserAssertion(AssertionType.ELEMENT_COUNT, selector=".cart-items .item", expected_value=2, description="Verify 2 items in cart"),
                UserAssertion(AssertionType.PAGE_URL, expected_value="/checkout", description="Verify checkout page"),
                UserAssertion(AssertionType.ELEMENT_VISIBLE, selector=".checkout-form", description="Verify checkout form visible")
            ],
            critical=True,
            expected_duration=15.0
        )

    @staticmethod
    def create_form_submission_journey(base_url: str, form_data: Dict[str, str]) -> UserJourney:
        """Create a form submission journey"""
        steps = [
            UserAction(ActionType.NAVIGATE, value=f"{base_url}/contact", description="Navigate to contact form")
        ]

        # Add form field actions
        for field_name, field_value in form_data.items():
            steps.append(
                UserAction(
                    ActionType.TYPE,
                    selector=f"input[name='{field_name}'], textarea[name='{field_name}']",
                    value=field_value,
                    description=f"Fill {field_name} field"
                )
            )

        steps.extend([
            UserAction(ActionType.CLICK, selector="button[type='submit']", description="Submit form"),
            UserAction(ActionType.WAIT, value="3", description="Wait for submission")
        ])

        return UserJourney(
            name="Form Submission Flow",
            description="Fill and submit contact form",
            steps=steps,
            assertions=[
                UserAssertion(AssertionType.ELEMENT_VISIBLE, selector=".success-message", description="Verify success message"),
                UserAssertion(AssertionType.ELEMENT_TEXT, selector=".success-message", expected_value="Thank you for your message!", description="Verify success text")
            ],
            critical=False,
            expected_duration=12.0
        )


# Example usage
async def main():
    """Demonstrate advanced web testing capabilities"""

    print("🌐 Advanced Web Testing Demonstration")

    # Example user journey
    journey = UserJourneyTemplates.create_login_journey(
        "http://localhost:3000",
        "testuser@example.com",
        "password123"
    )

    # Test with Playwright
    if PLAYWRIGHT_AVAILABLE:
        print("\n🎭 Testing with Playwright...")
        playwright_adapter = AdvancedPlaywrightAdapter({
            "headless": True,
            "browser": "chromium"
        })

        if await playwright_adapter.initialize():
            result = await playwright_adapter.execute_user_journey(journey)
            print(f"   Status: {result.status}")
            print(f"   Steps: {result.steps_passed}/{result.steps_executed}")
            print(f"   Duration: {result.duration:.2f}s")

            await playwright_adapter.cleanup()

    # Test with Selenium
    if SELENIUM_AVAILABLE:
        print("\n🤖 Testing with Selenium...")
        selenium_adapter = AdvancedSeleniumAdapter({
            "headless": True
        })

        if await selenium_adapter.initialize():
            result = await selenium_adapter.execute_user_journey(journey)
            print(f"   Status: {result.status}")
            print(f"   Steps: {result.steps_passed}/{result.steps_executed}")
            print(f"   Duration: {result.duration:.2f}s")

            await selenium_adapter.cleanup()


if __name__ == "__main__":
    asyncio.run(main())